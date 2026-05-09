import styles from './Spinner.module.css';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

// 로딩 스피너 컴포넌트
export function Spinner({ size = 'md', label = '로딩 중...' }: SpinnerProps) {
  return (
    <div className={styles.wrapper} role="status" aria-label={label}>
      <div className={`${styles.spinner} ${styles[size]}`} />
      {label && <span className={styles.label}>{label}</span>}
    </div>
  );
}
