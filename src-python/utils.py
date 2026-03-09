import base64
from typing import Any, List, Dict, Optional
import json
import traceback
import logging
from logging.handlers import RotatingFileHandler

try:
    import requests
except Exception:
    requests = None  # type: ignore
import ipaddress
import socket

def validateDictStructure(data: dict, structure: dict) -> bool:
    if not isinstance(data, dict) or not isinstance(structure, dict):
        return False
    if set(data.keys()) != set(structure.keys()):
        return False
    for key, expected_type_or_structure in structure.items():
        if key not in data:
            return False
        value = data[key]
        if isinstance(expected_type_or_structure, dict):
            if not validateDictStructure(value, expected_type_or_structure):
                return False
        else:
            if not isinstance(value, expected_type_or_structure):
                return False
    return True

def isConnectedNetwork(url="http://www.bing.com", timeout=3) -> bool:
    if requests is None:
        return False
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False

def isAvailableWebSocketServer(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as chk:
            chk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            chk.bind((host, port))
        return True
    except Exception:
        return False

def isValidIpAddress(ip_address: str) -> bool:
    try:
        ipaddress.ip_address(ip_address)
        return True
    except ValueError:
        return False

def encodeBase64(data: str) -> Dict[str, Any]:
    try:
        return json.loads(base64.b64decode(data).decode('utf-8'))
    except Exception:
        errorLogging()
        return {}

def removeLog() -> None:
    try:
        import os
        if os.path.exists('process.log') and os.path.getsize('process.log') > 0:
            try:
                if os.path.exists('process.log.old'):
                    os.remove('process.log.old')
                os.rename('process.log', 'process.log.old')
            except Exception:
                pass
        with open('process.log', 'w', encoding="utf-8") as f:
            f.write("")
    except Exception:
        errorLogging()

def setupLogger(name: str, log_file: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    max_log_size = 10 * 1024 * 1024
    file_handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=1, encoding="utf-8", delay=True)
    file_handler.setLevel(level)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', None) == getattr(file_handler, 'baseFilename', None) for h in logger.handlers):
        logger.addHandler(file_handler)
    return logger

process_logger: Optional[logging.Logger] = None

def printLog(log: str, data: Any = None) -> None:
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)
    response = {"status": 348, "log": log, "data": str(data)}
    process_logger.info(response)
    print(json.dumps(response), flush=True)

def printResponse(status: int, endpoint: str, result: Any = None) -> None:
    global process_logger
    if process_logger is None:
        process_logger = setupLogger("process", "process.log", logging.INFO)
    response = {"status": status, "endpoint": endpoint, "result": result}
    process_logger.info(response)
    try:
        serialized_response = json.dumps(response)
    except Exception as e:
        errorLogging()
        error_json = json.dumps({"status": 500, "endpoint": endpoint, "result": {"error": "Failed to serialize response", "details": str(e)}})
        print(error_json, flush=True)
    else:
        print(serialized_response, flush=True)

error_logger: Optional[logging.Logger] = None

def errorLogging() -> None:
    global error_logger
    if error_logger is None:
        error_logger = setupLogger("error", "error.log", logging.ERROR)
    try:
        error_logger.error(traceback.format_exc())
    except Exception:
        print(traceback.format_exc(), flush=True)
