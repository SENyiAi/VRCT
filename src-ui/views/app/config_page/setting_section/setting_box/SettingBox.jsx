import { useStore_SelectedConfigTabId } from "@store";

import {
    Device,
    Appearance,
    Translation,
    Transcription,
    Others,
    AdvancedSettings,
    Vr,
    Hotkeys,
    Plugins,
    AboutVrct,
    Honkai,
} from "@setting_box";

export const SettingBox = () => {
    const { currentSelectedConfigTabId } = useStore_SelectedConfigTabId();
    switch (currentSelectedConfigTabId.data) {
        case "device":
            return <Device />;
        case "appearance":
            return <Appearance />;
        case "translation":
            return <Translation />;
        case "transcription":
            return <Transcription />;
        case "others":
            return <Others />;
        case "vr":
            return <Vr />;
        case "hotkeys":
            return <Hotkeys />;
        case "advanced_settings":
            return <AdvancedSettings />;
        case "plugins":
            return <Plugins />;
        case "about_vrct":
            return <AboutVrct />;
        case "honkai":
            return <Honkai />;

        default:
            return null;
    }
};