# 初期化のため、config.jsonの削除
import os
import time
import random
if os.path.exists("config.json"):
    os.remove("config.json")

from mainloop import main_instance

class Color:
	BLACK          = '\033[30m'#(文字)黒
	RED            = '\033[31m'#(文字)赤
	GREEN          = '\033[32m'#(文字)緑
	YELLOW         = '\033[33m'#(文字)黄
	BLUE           = '\033[34m'#(文字)青
	MAGENTA        = '\033[35m'#(文字)マゼンタ
	CYAN           = '\033[36m'#(文字)シアン
	WHITE          = '\033[37m'#(文字)白
	COLOR_DEFAULT  = '\033[39m'#文字色をデフォルトに戻す
	BOLD           = '\033[1m'#太字
	UNDERLINE      = '\033[4m'#下線
	INVISIBLE      = '\033[08m'#不可視
	REVERCE        = '\033[07m'#文字色と背景色を反転
	BG_BLACK       = '\033[40m'#(背景)黒
	BG_RED         = '\033[41m'#(背景)赤
	BG_GREEN       = '\033[42m'#(背景)緑
	BG_YELLOW      = '\033[43m'#(背景)黄
	BG_BLUE        = '\033[44m'#(背景)青
	BG_MAGENTA     = '\033[45m'#(背景)マゼンタ
	BG_CYAN        = '\033[46m'#(背景)シアン
	BG_WHITE       = '\033[47m'#(背景)白
	BG_DEFAULT     = '\033[49m'#背景色をデフォルトに戻す
	RESET          = '\033[0m'#全てリセット

class TestMainloop():
    def __init__(self):
        self.main = main_instance
        # Start mainloop threads
        self.main.start()

        # Ensure the watchdog can stop the mainloop cleanly
        def _none_watchdog():
            return None
        self.main.controller.setWatchdogCallback(_none_watchdog)
        self.main.controller.init()

        # mappingのすべてのstatusをTrueにする
        for key in self.main.mapping.keys():
            self.main.mapping[key]["status"] = True

        self.config_dict = {}
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/get/data/"):
                self.config_dict[endpoint.split("/")[-1]], _ = self.main.handleRequest(endpoint, None)
            elif endpoint.startswith("/set/disable/"):
                self.config_dict[endpoint.split("/")[-1]], _ = self.main.handleRequest(endpoint, None)
        print(self.config_dict, flush=True)

        self.validity_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/set/enable/") or endpoint.startswith("/set/disable/"):
                self.validity_endpoints.append(endpoint)

        self.set_data_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/set/data/"):
                self.set_data_endpoints.append(endpoint)
        # 新規: local LLM/API キー/モデル選択関連の存在確認ログ
        print(f"[DEBUG] set_data_endpoints count: {len(self.set_data_endpoints)}", flush=True)

        self.delete_data_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/delete/data/"):
                self.delete_data_endpoints.append(endpoint)

        self.run_endpoints = []
        for endpoint in self.main.mapping.keys():
            if endpoint.startswith("/run/"):
                self.run_endpoints.append(endpoint)

        self.test_results = {}

    def record_test_result(self, endpoint, status, result, expected_status):
        """
        テスト結果を記録する
        :param endpoint: テスト対象のエンドポイント
        :param status: 実際のステータスコード
        :param result: 実際の結果
        :param expected_status: 期待されるステータスコード
        """
        self.test_results[endpoint] = {
            "status": status,
            "result": result,
            "expected_status": expected_status,
            "success": status in expected_status
        }

    def test_endpoints_on_off_single(self, endpoint):
        success = False
        expected_status = [200]
        if endpoint.startswith("/set/enable/"):
            match endpoint:
                case "/set/enable/websocket_server":
                    expected_status = [200, 400]
                case _:
                    pass

            result, status = self.main.handleRequest(endpoint, None)
            if status in expected_status:
                if status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                success = True
            else:
                print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                print(f"Current config_dict: {self.config_dict}")
        elif endpoint.startswith("/set/disable/"):
            result, status = self.main.handleRequest(endpoint, None)
            if status in expected_status:
                if status == 200:
                    self.config_dict[endpoint.split("/")[-1]] = result
                print(f"-> {Color.GREEN}[PASS]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                success = True
            else:
                print(f"-> {Color.RED}[ERROR]{Color.RESET} endpoint:{endpoint} Status: {status}, Result: {result}")
                print(f"Current config_dict: {self.config_dict}")
        self.record_test_result(endpoint, status, result, expected_status)
        return success

    def test_endpoints_on_off_all(self):
        print("----ON/OFF系のエンドポイントのテスト----")
        for endpoint in self.validity_endpoints:
            print(f"Testing endpoint: {endpoint}", flush=True)
            self.test_endpoints_on_off_single(endpoint)
        print("----ON/OFF系のエンドポイントのテスト終了----")

    def test_endpoints_on_off_random(self):
        print("----ON/OFFでのランダムアクセスのテスト----")
        for i in range(1000):
            endpoint = random.choice(self.validity_endpoints)
            print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
            if self.test_endpoints_on_off_single(endpoint) is False:
                break

        # 最後にすべてOFFにして終了
        for endpoint in self.validity_endpoints:
            if endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
                time.sleep(0.2)
        print("----ON/OFFでのランダムアクセスのテスト終了----")

    def test_endpoints_on_off_continuous(self):
        print("----ON/OFF連続テスト----")
        endpoints = [
            "/set/enable/translation",
            "/set/disable/translation",
            "/set/enable/transcription_send",
            "/set/disable/transcription_send",
            "/set/enable/transcription_receive",
            "/set/disable/transcription_receive",
        #     "/set/enable/websocket_server",
        #     "/set/disable/websocket_server",
        ]
        for i in range(1000):
            endpoint = random.choice(endpoints)
            print(f"No.{i:04} Testing endpoint: {endpoint}", flush=True)
            if self.test_endpoints_on_off_single(endpoint) is False:
                break

        # 最後にすべてOFFにして終了
        for endpoint in self.validity_endpoints:
            if endpoint.startswith("/set/disable/"):
                result, status = self.main.handleRequest(endpoint, None)
        print("----ON/OFF連続テスト終了----")

    def test_set_data_endpoints_single(self, endpoint):
        success = False
        expected_status = [200]
        match endpoint:
            case "/set/data/selected_tab_no":
                data = random.choice(["1", "2", "3"])
            case "/set/data/selected_translation_engines":
                print("Fetching endpoint data for translation_engines...")
                self.config_dict["translation_engines"], _ = self.main.handleRequest("/get/data/selectable_translation_engines", None)
                translation_engines = self.config_dict.get("translation_engines", None)
                data = {}
                for i in ["1", "2", "3"]:
                    data[i] = random.choice(translation_engines)
            case "/set/data/selected_your_languages":
                self.config_dict["selectable_language_list"], _ = self.main.handleRequest("/get/data/selectable_language_list", None)
                selectable_language_list = self.config_dict.get("selectable_language_list", None)
                data = {}
                for i in ["1", "2", "3"]:
                    data[i] = {}
                    data[i]["1"] = random.choice(selectable_language_list) | {"enable": True}
            case "/set/data/selected_target_languages":
                self.config_dict["selectable_language_list"], _ = self.main.handleRequest("/get/data/selectable_language_list", None)
                selectable_language_list = self.config_dict.get("selectable_language_list", None)
                data = {}
                for i in ["1", "2", "3"]:
                    data[i] = {}
                    for j in ["1", "2", "3"]:
                        data[i][j] = random.choice(selectable_language_list) | {"enable": random.choice([True, False])}
            case "/set/data/selected_transcription_engine":
                self.config_dict["transcription_engines"], _ = self.main.handleRequest("/get/data/selectable_transcription_engines", None)
                transcription_engines = self.config_dict.get("transcription_engines", None)
                data = random.choice(transcription_engines)
            case "/set/data/transparency":
                data = random.randint(0, 100)
            case "/set/data/ui_scaling":
                data = random.randint(50, 200)
            case "/set/data/textbox_ui_scaling":
                data = random.randint(50, 200)
            case "/set/data/message_box_ratio":
                data = round(random.uniform(0.1, 0.9), 2)
            case "/set/data/send_message_button_type":
                data = random.choice(["show", "hide", "show_and_disable_enter_key"])
            case "/set/data/font_family":
                data = random.choice(["Arial", "Verdana", "Times New Roman"])
            case "/set/data/ui_language":
                data = random.choice(["en", "ja", "ko", "zh-Hant", "zh-Hans"])
            case "/set/data/main_window_geometry":
                data = {
                    "x_pos": random.randint(0, 1920),
                    "y_pos": random.randint(0, 1080),
                    "width": random.randint(800, 1920),
                    "height": random.randint(600, 1080)
                }