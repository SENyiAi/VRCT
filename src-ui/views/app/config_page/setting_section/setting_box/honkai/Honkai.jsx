import styles from "./Honkai.module.scss";

export const Honkai = () => {
    return (
        <div className={styles.container}>
            <p className={styles.title}>Honkai</p>
            <p className={styles.placeholder_text}>这里是开发者选项</p>
        </div>
    );
};
