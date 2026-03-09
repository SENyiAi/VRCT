import { useEffect, useState } from "react";
import { useI18n } from "@useI18n";
import styles from "./Translation.module.scss";
import { updateLabelsById, arrayToObject } from "@utils";
import { useStore_IsBreakPoint } from "@store";

import {
    useTranslation,

    useSaveButtonLogic,
} from "@logics_configs";

import {
    DownloadModelsContainer,
    AuthKeyContainer,
    MultiDropdownMenuContainer,
    EntryWithSaveButtonContainer,
    RadioButtonContainer,
    DropdownMenuContainer,
    ConnectionCheckButtonContainer,
    SwitchBoxContainer,

    useOnMouseLeaveDropdownMenu,
} from "../_templates/Templates";

import {
    DropdownMenu,
    MultiDropdownMenu,
    LabelComponent,
    ConnectionCheckButton,
} from "../_components";

import {
    deepl_auth_key_url,
    plamo_auth_key_url,
    gemini_auth_key_url,
    openai_auth_key_url,
    groq_auth_key_url,
    openrouter_auth_key_url,
    siliconflow_auth_key_url,
} from "@ui_configs";

import { useLLMConnection } from "@logics_common";

export const Translation = () => {
    return (
        <>
            <CTranslate2WeightType_Box />
            <TranslationComputeDevice_Box />

            <DeepLAuthKey_Box />

            <PlamoAuthKey_Box />
            <PlamoModelContainer />

            <GeminiAuthKey_Box />
            <GeminiModelContainer />

            <OpenAIAuthKey_Box />
            <OpenAIModelContainer />

            <CustomOpenAIConnectionCheck_Box />
            <CustomOpenAIURL_Box />
            <CustomOpenAIAuthKey_Box />
            <CustomOpenAIModel_Box />
            <CustomOpenAIMaxTokens_Box />
            <CustomOpenAITemperature_Box />
            <CustomOpenAICustomSystemPrompt_Box />
            <CustomOpenAIAsrCorrection_Box />

            <CustomOpenAI2ConnectionCheck_Box />
            <CustomOpenAI2URL_Box />
            <CustomOpenAI2AuthKey_Box />
            <CustomOpenAI2Model_Box />
            <CustomOpenAI2MaxTokens_Box />
            <CustomOpenAI2Temperature_Box />
            <CustomOpenAI2CustomSystemPrompt_Box />
            <CustomOpenAI2AsrCorrection_Box />

            <CustomOpenAI3ConnectionCheck_Box />
            <CustomOpenAI3URL_Box />
            <CustomOpenAI3AuthKey_Box />
            <CustomOpenAI3Model_Box />
            <CustomOpenAI3MaxTokens_Box />
            <CustomOpenAI3Temperature_Box />
            <CustomOpenAI3CustomSystemPrompt_Box />
            <CustomOpenAI3AsrCorrection_Box />

            <TranslationFallback_Box />

            <GroqAuthKey_Box />
            <GroqModelContainer />

            <OpenRouterAuthKey_Box />
            <OpenRouterModelContainer />

            <SiliconFlowAuthKey_Box />
            <SiliconFlowModelContainer />
            <SiliconFlowMaxTokens_Box />
            <SiliconFlowTemperature_Box />
            <SiliconFlowCustomSystemPrompt_Box />
            <SiliconFlowAsrCorrection_Box />
            <SiliconFlowEnableThinking_Box />

            <LMStudioConnectionCheck_Box />
            <LMStudioURL_Box />
            <LMStudioModelContainer />

            <OllamaConnectionCheck_Box />
            <OllamaModelContainer />
        </>
    );
};

const CTranslate2WeightType_Box = () => {
    const { t } = useI18n();
    const {
        currentCTranslate2WeightTypeStatus,
        pendingCTranslate2WeightTypeStatus,
        downloadCTranslate2WeightTypeStatus,

        currentSelectedCTranslate2WeightType,
        setSelectedCTranslate2WeightType,
    } = useTranslation();

    const selectFunction = (id) => {
        setSelectedCTranslate2WeightType(id);
    };

    const downloadStartFunction = (id) => {
        pendingCTranslate2WeightTypeStatus(id);
        downloadCTranslate2WeightTypeStatus(id);
    };


    const c_translate2_weight_types_object = currentCTranslate2WeightTypeStatus.data.map(item => {
        return {
            ...item,
            label: `${item.id} (${item.capacity})`,
        };
    });


    return (
        <>
            <DownloadModelsContainer
                label={t(
                    "config_page.translation.ctranslate2_weight_type.label",
                    {ctranslate2: "CTranslate2"}
                )}
                desc={t(
                    "config_page.translation.ctranslate2_weight_type.desc",
                    {ctranslate2: "CTranslate2"}
                )}
                name="ctranslate2_weight_type"
                options={c_translate2_weight_types_object}
                checked_variable={currentSelectedCTranslate2WeightType}
                selectFunction={selectFunction}
                downloadStartFunction={downloadStartFunction}
            />
        </>
    );
};
// Duplicate
const TranslationComputeDevice_Box = () => {
    const { t } = useI18n();
    const {
        currentSelectableTranslationComputeDeviceList,
        currentSelectedTranslationComputeDevice,
        setSelectedTranslationComputeDevice,
        currentSelectedTranslationComputeType,
        setSelectedTranslationComputeType,
    } = useTranslation();

    const list_for_ui = transformDeviceArray(currentSelectableTranslationComputeDeviceList.data);

    const target_index = findKeyByDeviceValue(currentSelectableTranslationComputeDeviceList.data, currentSelectedTranslationComputeDevice.data);

    const DEFAULT_ORDER = [
        "auto",
        "int8",
        "int8_bfloat16",
        "int8_float16",
        "int8_float32",
        "bfloat16",
        "float16",
        "int16",
        "float32"
    ];

    const sortComputeTypesArray = (compute_types_array = [], order) => {
        const src_set = new Set(compute_types_array);

        const from_order = order.filter((id) => src_set.has(id));

        const invalid_ids = compute_types_array.filter((id) => !order.includes(id));
        if (invalid_ids.length > 0) {
            console.error("[sortComputeTypesArray] Unsupported compute types ignored:", invalid_ids);
        }

        return from_order;
    };


    const buildSimpleLabels = (ordered_array = []) => {
        const n = ordered_array.length;
        if (n === 0) return {};

        const labels = {};

        ordered_array.forEach((id, idx) => {
            if (idx === 0 && id === "auto") {
                labels[id] = t("config_page.common.compute_device.type_template_auto");
                return;
            }

            if (idx === 1) {
                labels[id] = t(
                    "config_page.common.compute_device.type_template_low",
                    { type_name: id }
                );
                return;
            }

            if (idx === n - 1) {
                labels[id] = t(
                    "config_page.common.compute_device.type_template_high",
                    { type_name: id }
                );
                return;
            }

            labels[id] = id;
        });

        return labels;
    };


    const computeTypesArray = currentSelectableTranslationComputeDeviceList.data[target_index].compute_types;

    const ordered_array = sortComputeTypesArray(computeTypesArray, DEFAULT_ORDER);

    const new_compute_types_labels = buildSimpleLabels(ordered_array);

    const selectFunction_ComputeDevice = (selected_data) => {
        const target_obj = currentSelectableTranslationComputeDeviceList.data[selected_data.selected_id];
        setSelectedTranslationComputeDevice(target_obj);
    };

    const selectFunction_ComputeType = (selected_data) => {
        setSelectedTranslationComputeType(selected_data.selected_id);
    };

    const is_disabled_selector = currentSelectedTranslationComputeDevice.state === "pending" || currentSelectedTranslationComputeType.state === "pending";

    return (
        <MultiDropdownMenuContainer
            label={t("config_page.translation.translation_compute_device.label")}
            desc={t("config_page.common.compute_device.desc")}
            dropdown_settings={[
                {
                    dropdown_id: "translation_compute_device",
                    secondary_label: t("config_page.common.compute_device.label_device"),
                    selected_id: target_index,
                    list: list_for_ui,
                    selectFunction: selectFunction_ComputeDevice,
                    state: currentSelectedTranslationComputeDevice.state,
                    style: { maxWidth: "20rem", minWidth: "10rem" },
                    is_disabled: is_disabled_selector,
                },
                {
                    dropdown_id: "translation_compute_type",
                    secondary_label: t("config_page.common.compute_device.label_type"),
                    selected_id: currentSelectedTranslationComputeType.data,
                    list: new_compute_types_labels,
                    selectFunction: selectFunction_ComputeType,
                    state: currentSelectedTranslationComputeType.state,
                    is_disabled: is_disabled_selector,
                }
            ]}
        />
    );
};

const DeepLAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentDeepLAuthKey, setDeepLAuthKey, deleteDeepLAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentDeepLAuthKey.data,
        state: currentDeepLAuthKey.state,
        setFunction: setDeepLAuthKey,
        deleteFunction: deleteDeepLAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.deepl_auth_key.label")}
                desc={t(
                    "config_page.translation.deepl_auth_key.desc",
                    {translator: t("main_page.translator")}
                )}
                webpage_url={deepl_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentDeepLAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
            />
        </>
    );
};

const PlamoAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentPlamoAuthKey, setPlamoAuthKey, deletePlamoAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentPlamoAuthKey.data,
        state: currentPlamoAuthKey.state,
        setFunction: setPlamoAuthKey,
        deleteFunction: deletePlamoAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.plamo_auth_key.label")}
                // desc="Plamo Auth Desc"
                webpage_url={plamo_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentPlamoAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const PlamoModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectablePlamoModelList,

        currentSelectedPlamoModel,
        setSelectedPlamoModel,

        currentPlamoAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedPlamoModel(selected_data.selected_id);
    };


    let selected_label = (!currentPlamoAuthKey.data && !currentSelectedPlamoModel.data) ? t("config_page.common.correct_auth_key_required") : currentSelectedPlamoModel.data;


    return (
        <DropdownMenuContainer
            dropdown_id="select_plamo_model"
            label={t("config_page.translation.select_plamo_model.label")}
            selected_id={selected_label}
            list={currentSelectablePlamoModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedPlamoModel.state}
            is_disabled={!currentPlamoAuthKey.data}
        />
    );
};



const GeminiAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentGeminiAuthKey, setGeminiAuthKey, deleteGeminiAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentGeminiAuthKey.data,
        state: currentGeminiAuthKey.state,
        setFunction: setGeminiAuthKey,
        deleteFunction: deleteGeminiAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.gemini_auth_key.label")}
                // desc="Gemini Auth Desc"
                webpage_url={gemini_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentGeminiAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const GeminiModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableGeminiModelList,

        currentSelectedGeminiModel,
        setSelectedGeminiModel,

        currentGeminiAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedGeminiModel(selected_data.selected_id);
    };

    let selected_label = (!currentGeminiAuthKey.data && !currentSelectedGeminiModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedGeminiModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_gemini_model"
            label={t("config_page.translation.select_gemini_model.label")}
            selected_id={selected_label}
            list={currentSelectableGeminiModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedGeminiModel.state}
            is_disabled={!currentGeminiAuthKey.data}
        />
    );
};


const OpenAIAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentOpenAIAuthKey, setOpenAIAuthKey, deleteOpenAIAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOpenAIAuthKey.data,
        state: currentOpenAIAuthKey.state,
        setFunction: setOpenAIAuthKey,
        deleteFunction: deleteOpenAIAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.openai_auth_key.label")}
                // desc="OpenAI Auth Desc"
                webpage_url={openai_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentOpenAIAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const OpenAIModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableOpenAIModelList,

        currentSelectedOpenAIModel,
        setSelectedOpenAIModel,

        currentOpenAIAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedOpenAIModel(selected_data.selected_id);
    };

    let selected_label = (!currentOpenAIAuthKey.data && !currentSelectedOpenAIModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedOpenAIModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_openai_model"
            label={t("config_page.translation.select_openai_model.label")}
            selected_id={selected_label}
            list={currentSelectableOpenAIModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedOpenAIModel.state}
            is_disabled={!currentOpenAIAuthKey.data}
        />
    );
};


const CustomOpenAIConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsCustomOpenAIConnected, checkConnection_CustomOpenAI } = useLLMConnection();

    return (
        <>
            <ConnectionCheckButtonContainer
                label={t("config_page.translation.custom_openai_connection_check.label")}
                variable={currentIsCustomOpenAIConnected.data}
                state={currentIsCustomOpenAIConnected.state}
                checkFunction={checkConnection_CustomOpenAI}
                remove_border_bottom={true}
            />
        </>
    );
};
const CustomOpenAIURL_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAIURL, setCustomOpenAIURL } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAIURL.data,
        state: currentCustomOpenAIURL.state,
        setFunction: setCustomOpenAIURL,
    });

    return (
        <>
            <EntryWithSaveButtonContainer
                label={t("config_page.translation.custom_openai_url.label")}
                variable={variable}
                saveFunction={saveFunction}
                onChangeFunction={onChangeFunction}
                state={currentCustomOpenAIURL.state}
                remove_border_bottom={true}
            />
        </>
    );
};
const CustomOpenAIAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAIAuthKey, setCustomOpenAIAuthKey, deleteCustomOpenAIAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAIAuthKey.data,
        state: currentCustomOpenAIAuthKey.state,
        setFunction: setCustomOpenAIAuthKey,
        deleteFunction: deleteCustomOpenAIAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.custom_openai_auth_key.label")}
                variable={variable}
                state={currentCustomOpenAIAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const CustomOpenAIModel_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAIModel, setCustomOpenAIModel } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAIModel.data,
        state: currentCustomOpenAIModel.state,
        setFunction: setCustomOpenAIModel,
    });

    return (
        <>
            <EntryWithSaveButtonContainer
                label={t("config_page.translation.custom_openai_model.label")}
                variable={variable}
                saveFunction={saveFunction}
                onChangeFunction={onChangeFunction}
                state={currentCustomOpenAIModel.state}
                remove_border_bottom={true}
            />
        </>
    );
};

const CustomOpenAIAsrCorrection_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAIAsrCorrection, toggleCustomOpenAIAsrCorrection } = useTranslation();

    return (
        <>
            <SwitchBoxContainer
                label={t("config_page.translation.custom_openai_asr_correction.label")}
                desc={t("config_page.translation.custom_openai_asr_correction.desc")}
                variable={currentCustomOpenAIAsrCorrection}
                toggleFunction={toggleCustomOpenAIAsrCorrection}
                remove_border_bottom={true}
            />
        </>
    );
};

// --- Extra params for Custom OpenAI slot 1 ---
const CustomOpenAIMaxTokens_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAIMaxTokens, setCustomOpenAIMaxTokens } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAIMaxTokens.data,
        state: currentCustomOpenAIMaxTokens.state,
        setFunction: setCustomOpenAIMaxTokens,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_max_tokens.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAIMaxTokens.state}
            remove_border_bottom={true}
        />
    );
};

const CustomOpenAITemperature_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAITemperature, setCustomOpenAITemperature } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAITemperature.data,
        state: currentCustomOpenAITemperature.state,
        setFunction: setCustomOpenAITemperature,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_temperature.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAITemperature.state}
            remove_border_bottom={true}
        />
    );
};

const CustomOpenAICustomSystemPrompt_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAICustomSystemPrompt, setCustomOpenAICustomSystemPrompt } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAICustomSystemPrompt.data,
        state: currentCustomOpenAICustomSystemPrompt.state,
        setFunction: setCustomOpenAICustomSystemPrompt,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_custom_system_prompt.label")}
            desc={t("config_page.translation.custom_openai_custom_system_prompt.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAICustomSystemPrompt.state}
            remove_border_bottom={true}
        />
    );
};

// --- Custom OpenAI 2 ---
const CustomOpenAI2ConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsCustomOpenAI2Connected, checkConnection_CustomOpenAI2 } = useLLMConnection();

    return (
        <ConnectionCheckButtonContainer
            label={t("config_page.translation.custom_openai_2_connection_check.label")}
            variable={currentIsCustomOpenAI2Connected.data}
            state={currentIsCustomOpenAI2Connected.state}
            checkFunction={checkConnection_CustomOpenAI2}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2URL_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2URL, setCustomOpenAI2URL } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI2URL.data,
        state: currentCustomOpenAI2URL.state,
        setFunction: setCustomOpenAI2URL,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_2_url.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI2URL.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2AuthKey_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2AuthKey, setCustomOpenAI2AuthKey, deleteCustomOpenAI2AuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI2AuthKey.data,
        state: currentCustomOpenAI2AuthKey.state,
        setFunction: setCustomOpenAI2AuthKey,
        deleteFunction: deleteCustomOpenAI2AuthKey,
    });

    return (
        <AuthKeyContainer
            label={t("config_page.translation.custom_openai_2_auth_key.label")}
            variable={variable}
            state={currentCustomOpenAI2AuthKey.state}
            onChangeFunction={onChangeFunction}
            saveFunction={saveFunction}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2Model_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2Model, setCustomOpenAI2Model } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI2Model.data,
        state: currentCustomOpenAI2Model.state,
        setFunction: setCustomOpenAI2Model,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_2_model.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI2Model.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2MaxTokens_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2MaxTokens, setCustomOpenAI2MaxTokens } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI2MaxTokens.data,
        state: currentCustomOpenAI2MaxTokens.state,
        setFunction: setCustomOpenAI2MaxTokens,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_2_max_tokens.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI2MaxTokens.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2Temperature_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2Temperature, setCustomOpenAI2Temperature } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI2Temperature.data,
        state: currentCustomOpenAI2Temperature.state,
        setFunction: setCustomOpenAI2Temperature,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_2_temperature.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI2Temperature.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2CustomSystemPrompt_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2CustomSystemPrompt, setCustomOpenAI2CustomSystemPrompt } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI2CustomSystemPrompt.data,
        state: currentCustomOpenAI2CustomSystemPrompt.state,
        setFunction: setCustomOpenAI2CustomSystemPrompt,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_2_custom_system_prompt.label")}
            desc={t("config_page.translation.custom_openai_custom_system_prompt.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI2CustomSystemPrompt.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI2AsrCorrection_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI2AsrCorrection, toggleCustomOpenAI2AsrCorrection } = useTranslation();

    return (
        <SwitchBoxContainer
            label={t("config_page.translation.custom_openai_2_asr_correction.label")}
            desc={t("config_page.translation.custom_openai_asr_correction.desc")}
            variable={currentCustomOpenAI2AsrCorrection}
            toggleFunction={toggleCustomOpenAI2AsrCorrection}
            remove_border_bottom={true}
        />
    );
};

// --- Custom OpenAI 3 ---
const CustomOpenAI3ConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsCustomOpenAI3Connected, checkConnection_CustomOpenAI3 } = useLLMConnection();

    return (
        <ConnectionCheckButtonContainer
            label={t("config_page.translation.custom_openai_3_connection_check.label")}
            variable={currentIsCustomOpenAI3Connected.data}
            state={currentIsCustomOpenAI3Connected.state}
            checkFunction={checkConnection_CustomOpenAI3}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3URL_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3URL, setCustomOpenAI3URL } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI3URL.data,
        state: currentCustomOpenAI3URL.state,
        setFunction: setCustomOpenAI3URL,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_3_url.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI3URL.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3AuthKey_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3AuthKey, setCustomOpenAI3AuthKey, deleteCustomOpenAI3AuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI3AuthKey.data,
        state: currentCustomOpenAI3AuthKey.state,
        setFunction: setCustomOpenAI3AuthKey,
        deleteFunction: deleteCustomOpenAI3AuthKey,
    });

    return (
        <AuthKeyContainer
            label={t("config_page.translation.custom_openai_3_auth_key.label")}
            variable={variable}
            state={currentCustomOpenAI3AuthKey.state}
            onChangeFunction={onChangeFunction}
            saveFunction={saveFunction}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3Model_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3Model, setCustomOpenAI3Model } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI3Model.data,
        state: currentCustomOpenAI3Model.state,
        setFunction: setCustomOpenAI3Model,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_3_model.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI3Model.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3MaxTokens_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3MaxTokens, setCustomOpenAI3MaxTokens } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI3MaxTokens.data,
        state: currentCustomOpenAI3MaxTokens.state,
        setFunction: setCustomOpenAI3MaxTokens,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_3_max_tokens.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI3MaxTokens.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3Temperature_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3Temperature, setCustomOpenAI3Temperature } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI3Temperature.data,
        state: currentCustomOpenAI3Temperature.state,
        setFunction: setCustomOpenAI3Temperature,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_3_temperature.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI3Temperature.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3CustomSystemPrompt_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3CustomSystemPrompt, setCustomOpenAI3CustomSystemPrompt } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentCustomOpenAI3CustomSystemPrompt.data,
        state: currentCustomOpenAI3CustomSystemPrompt.state,
        setFunction: setCustomOpenAI3CustomSystemPrompt,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.custom_openai_3_custom_system_prompt.label")}
            desc={t("config_page.translation.custom_openai_custom_system_prompt.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentCustomOpenAI3CustomSystemPrompt.state}
            remove_border_bottom={true}
        />
    );
};
const CustomOpenAI3AsrCorrection_Box = () => {
    const { t } = useI18n();
    const { currentCustomOpenAI3AsrCorrection, toggleCustomOpenAI3AsrCorrection } = useTranslation();

    return (
        <SwitchBoxContainer
            label={t("config_page.translation.custom_openai_3_asr_correction.label")}
            desc={t("config_page.translation.custom_openai_asr_correction.desc")}
            variable={currentCustomOpenAI3AsrCorrection}
            toggleFunction={toggleCustomOpenAI3AsrCorrection}
            remove_border_bottom={true}
        />
    );
};

// --- Translation Fallback ---
const TranslationFallback_Box = () => {
    const { t } = useI18n();
    const {
        currentTranslationFallbackEnabled, toggleTranslationFallbackEnabled,
        currentTranslationFallbackTimeout, setTranslationFallbackTimeout,
        currentTranslationFallbackEngine, setTranslationFallbackEngine,
    } = useTranslation();

    const { variable: timeoutVar, onChangeFunction: onChangeTimeout, saveFunction: saveTimeout } = useSaveButtonLogic({
        variable: currentTranslationFallbackTimeout.data,
        state: currentTranslationFallbackTimeout.state,
        setFunction: setTranslationFallbackTimeout,
    });

    const { variable: engineVar, onChangeFunction: onChangeEngine, saveFunction: saveEngine } = useSaveButtonLogic({
        variable: currentTranslationFallbackEngine.data,
        state: currentTranslationFallbackEngine.state,
        setFunction: setTranslationFallbackEngine,
    });

    return (
        <>
            <SwitchBoxContainer
                label={t("config_page.translation.translation_fallback_enabled.label")}
                desc={t("config_page.translation.translation_fallback_enabled.desc")}
                variable={currentTranslationFallbackEnabled}
                toggleFunction={toggleTranslationFallbackEnabled}
                remove_border_bottom={true}
            />
            <EntryWithSaveButtonContainer
                label={t("config_page.translation.translation_fallback_timeout.label")}
                variable={timeoutVar}
                saveFunction={saveTimeout}
                onChangeFunction={onChangeTimeout}
                state={currentTranslationFallbackTimeout.state}
                remove_border_bottom={true}
            />
            <EntryWithSaveButtonContainer
                label={t("config_page.translation.translation_fallback_engine.label")}
                variable={engineVar}
                saveFunction={saveEngine}
                onChangeFunction={onChangeEngine}
                state={currentTranslationFallbackEngine.state}
            />
        </>
    );
};


const GroqAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentGroqAuthKey, setGroqAuthKey, deleteGroqAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentGroqAuthKey.data,
        state: currentGroqAuthKey.state,
        setFunction: setGroqAuthKey,
        deleteFunction: deleteGroqAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.groq_auth_key.label")}
                // desc="Groq Auth Desc"
                webpage_url={groq_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentGroqAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const GroqModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableGroqModelList,

        currentSelectedGroqModel,
        setSelectedGroqModel,

        currentGroqAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedGroqModel(selected_data.selected_id);
    };

    let selected_label = (!currentGroqAuthKey.data && !currentSelectedGroqModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedGroqModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_groq_model"
            label={t("config_page.translation.select_groq_model.label")}
            selected_id={selected_label}
            list={currentSelectableGroqModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedGroqModel.state}
            is_disabled={!currentGroqAuthKey.data}
        />
    );
};


const OpenRouterAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentOpenRouterAuthKey, setOpenRouterAuthKey, deleteOpenRouterAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentOpenRouterAuthKey.data,
        state: currentOpenRouterAuthKey.state,
        setFunction: setOpenRouterAuthKey,
        deleteFunction: deleteOpenRouterAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.openrouter_auth_key.label")}
                // desc="OpenRouter Auth Desc"
                webpage_url={openrouter_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentOpenRouterAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const OpenRouterModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableOpenRouterModelList,

        currentSelectedOpenRouterModel,
        setSelectedOpenRouterModel,

        currentOpenRouterAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedOpenRouterModel(selected_data.selected_id);
    };

    let selected_label = (!currentOpenRouterAuthKey.data && !currentSelectedOpenRouterModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedOpenRouterModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_openrouter_model"
            label={t("config_page.translation.select_openrouter_model.label")}
            selected_id={selected_label}
            list={currentSelectableOpenRouterModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedOpenRouterModel.state}
            is_disabled={!currentOpenRouterAuthKey.data}
        />
    );
};

const SiliconFlowAuthKey_Box = () => {
    const { t } = useI18n();
    const { currentSiliconFlowAuthKey, setSiliconFlowAuthKey, deleteSiliconFlowAuthKey } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentSiliconFlowAuthKey.data,
        state: currentSiliconFlowAuthKey.state,
        setFunction: setSiliconFlowAuthKey,
        deleteFunction: deleteSiliconFlowAuthKey,
    });

    return (
        <>
            <AuthKeyContainer
                label={t("config_page.translation.siliconflow_auth_key.label")}
                webpage_url={siliconflow_auth_key_url}
                open_webpage_label={t("config_page.common.open_auth_key_webpage")}
                variable={variable}
                state={currentSiliconFlowAuthKey.state}
                onChangeFunction={onChangeFunction}
                saveFunction={saveFunction}
                remove_border_bottom={true}
            />
        </>
    );
};
const SiliconFlowModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableSiliconFlowModelList,

        currentSelectedSiliconFlowModel,
        setSelectedSiliconFlowModel,

        currentSiliconFlowAuthKey,
    } = useTranslation();


    const selectFunction = (selected_data) => {
        setSelectedSiliconFlowModel(selected_data.selected_id);
    };

    let selected_label = (!currentSiliconFlowAuthKey.data && !currentSelectedSiliconFlowModel.data)
        ? t("config_page.common.correct_auth_key_required")
        : currentSelectedSiliconFlowModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_siliconflow_model"
            label={t("config_page.translation.select_siliconflow_model.label")}
            selected_id={selected_label}
            list={currentSelectableSiliconFlowModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedSiliconFlowModel.state}
            is_disabled={!currentSiliconFlowAuthKey.data}
        />
    );
};

// --- Extra params for SiliconFlow ---
const SiliconFlowAsrCorrection_Box = () => {
    const { t } = useI18n();
    const { currentSiliconFlowAsrCorrection, toggleSiliconFlowAsrCorrection } = useTranslation();

    return (
        <SwitchBoxContainer
            label={t("config_page.translation.siliconflow_asr_correction.label")}
            desc={t("config_page.translation.siliconflow_asr_correction.desc")}
            variable={currentSiliconFlowAsrCorrection}
            toggleFunction={toggleSiliconFlowAsrCorrection}
            remove_border_bottom={true}
        />
    );
};

const SiliconFlowEnableThinking_Box = () => {
    const { t } = useI18n();
    const { currentSiliconFlowEnableThinking, toggleSiliconFlowEnableThinking } = useTranslation();

    return (
        <SwitchBoxContainer
            label={t("config_page.translation.siliconflow_enable_thinking.label")}
            desc={t("config_page.translation.siliconflow_enable_thinking.desc")}
            variable={currentSiliconFlowEnableThinking}
            toggleFunction={toggleSiliconFlowEnableThinking}
            remove_border_bottom={true}
        />
    );
};

const SiliconFlowMaxTokens_Box = () => {
    const { t } = useI18n();
    const { currentSiliconFlowMaxTokens, setSiliconFlowMaxTokens } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentSiliconFlowMaxTokens.data,
        state: currentSiliconFlowMaxTokens.state,
        setFunction: setSiliconFlowMaxTokens,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.siliconflow_max_tokens.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentSiliconFlowMaxTokens.state}
            remove_border_bottom={true}
        />
    );
};

const SiliconFlowTemperature_Box = () => {
    const { t } = useI18n();
    const { currentSiliconFlowTemperature, setSiliconFlowTemperature } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentSiliconFlowTemperature.data,
        state: currentSiliconFlowTemperature.state,
        setFunction: setSiliconFlowTemperature,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.siliconflow_temperature.label")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentSiliconFlowTemperature.state}
            remove_border_bottom={true}
        />
    );
};

const SiliconFlowCustomSystemPrompt_Box = () => {
    const { t } = useI18n();
    const { currentSiliconFlowCustomSystemPrompt, setSiliconFlowCustomSystemPrompt } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentSiliconFlowCustomSystemPrompt.data,
        state: currentSiliconFlowCustomSystemPrompt.state,
        setFunction: setSiliconFlowCustomSystemPrompt,
    });

    return (
        <EntryWithSaveButtonContainer
            label={t("config_page.translation.siliconflow_custom_system_prompt.label")}
            desc={t("config_page.translation.siliconflow_custom_system_prompt.desc")}
            variable={variable}
            saveFunction={saveFunction}
            onChangeFunction={onChangeFunction}
            state={currentSiliconFlowCustomSystemPrompt.state}
            remove_border_bottom={true}
        />
    );
};

const LMStudioConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsLMStudioConnected, checkConnection_LMStudio } = useLLMConnection();

    return (
        <>
            <ConnectionCheckButtonContainer
                label={t("config_page.translation.lmstudio_connection_check.label")}
                variable={currentIsLMStudioConnected.data}
                state={currentIsLMStudioConnected.state}
                checkFunction={checkConnection_LMStudio}
                remove_border_bottom={true}
                // width="10rem"
            />
        </>
    );
};
const LMStudioURL_Box = () => {
    const { t } = useI18n();
    const { currentLMStudioURL, setLMStudioURL, deleteLMStudioURL } = useTranslation();

    const { variable, onChangeFunction, saveFunction } = useSaveButtonLogic({
        variable: currentLMStudioURL.data,
        state: currentLMStudioURL.state,
        setFunction: setLMStudioURL,
        deleteFunction: deleteLMStudioURL,
    });

    return (
        <>
            <EntryWithSaveButtonContainer
                label="LM Studio URL"
                // label={t("config_page.translation.lmstudio_url.label")}
                // desc={t("config_page.translation.lmstudio_url.desc")}
                variable={variable}
                saveFunction={saveFunction}
                onChangeFunction={onChangeFunction}
                state={currentLMStudioURL.state}
                remove_border_bottom={true}
                // width="10rem"
            />
        </>
    );
};
const LMStudioModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableLMStudioModelList,

        currentSelectedLMStudioModel,
        setSelectedLMStudioModel,
    } = useTranslation();

    const { currentIsLMStudioConnected } = useLLMConnection();

    const selectFunction = (selected_data) => {
        setSelectedLMStudioModel(selected_data.selected_id);
    };

    let selected_label = (!currentIsLMStudioConnected.data && !currentSelectedLMStudioModel.data)
        ? t("config_page.translation.select_lmstudio_model.connection_required")
        : currentSelectedLMStudioModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_lmstudio_model"
            label={t("config_page.translation.select_lmstudio_model.label")}
            selected_id={selected_label}
            list={currentSelectableLMStudioModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedLMStudioModel.state}
            is_disabled={!currentIsLMStudioConnected.data}
        />
    );
};

const OllamaConnectionCheck_Box = () => {
    const { t } = useI18n();
    const { currentIsOllamaConnected, checkConnection_Ollama } = useLLMConnection();

    return (
        <>
            <ConnectionCheckButtonContainer
                label={t("config_page.translation.ollama_connection_check.label")}
                variable={currentIsOllamaConnected.data}
                state={currentIsOllamaConnected.state}
                checkFunction={checkConnection_Ollama}
                remove_border_bottom={true}
                // width="10rem"
            />
        </>
    );
};
const OllamaModelContainer = () => {
    const { t } = useI18n();
    const {
        currentSelectableOllamaModelList,

        currentSelectedOllamaModel,
        setSelectedOllamaModel,
    } = useTranslation();

    const { currentIsOllamaConnected } = useLLMConnection();

    const selectFunction = (selected_data) => {
        setSelectedOllamaModel(selected_data.selected_id);
    };

    let selected_label = (!currentIsOllamaConnected.data && !currentSelectedOllamaModel.data)
        ? t("config_page.translation.select_ollama_model.connection_required")
        : currentSelectedOllamaModel.data;

    return (
        <DropdownMenuContainer
            dropdown_id="select_ollama_model"
            label={t("config_page.translation.select_ollama_model.label")}
            selected_id={selected_label}
            list={currentSelectableOllamaModelList.data}
            selectFunction={selectFunction}
            state={currentSelectedOllamaModel.state}
            is_disabled={!currentIsOllamaConnected.data}
        />
    );
};


// Duplicate
const transformDeviceArray = (devices) => {
    const name_counts = Object.values(devices).reduce((counts, device) => {
        const name = device.device_name;
        counts[name] = (counts[name] || 0) + 1;
        return counts;
    }, {});

    const name_indices = {};
    const result = {};

    Object.entries(devices).forEach(([key, device]) => {
        const name = device.device_name;

        if (name_counts[name] > 1) {
            name_indices[name] = (name_indices[name] || 0);
            const value = `${name}:${name_indices[name]}`;
            name_indices[name]++;
            result[key] = value;
        } else {
            result[key] = name;
        }
    });

    return result;
};

const findKeyByDeviceValue = (devices, target_value) => {
    for (const [key, value] of Object.entries(devices)) {
        if (
            value.device === target_value.device &&
            value.device_index === target_value.device_index &&
            value.device_name === target_value.device_name
        ) {
            return parseInt(key);
        }
    }
    return null;
};