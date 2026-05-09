import { useCallback } from 'react';
import { useAppStore } from '../../store';
import { generateMosaic } from '../../utils/api';
import type { MosaicOptions } from '../../types';
import styles from './OptionsPanel.module.css';

// 타일 크기 선택지
const TILE_SIZE_OPTIONS = [16, 32, 64, 128] as const;

export function OptionsPanel() {
  const sessionId = useAppStore((state) => state.sessionId);
  const targetImageId = useAppStore((state) => state.targetImageId);
  const mosaicOptions = useAppStore((state) => state.mosaicOptions);
  const updateOptions = useAppStore((state) => state.updateOptions);
  const updateJob = useAppStore((state) => state.updateJob);
  const setStep = useAppStore((state) => state.setStep);
  const addToast = useAppStore((state) => state.addToast);

  const canGenerate = targetImageId !== null;

  // 옵션 변경 핸들러 (제네릭으로 타입 안전 보장)
  const handleChange = useCallback(
    <K extends keyof MosaicOptions>(key: K, value: MosaicOptions[K]) => {
      updateOptions({ [key]: value } as Partial<MosaicOptions>);
    },
    [updateOptions]
  );

  // 모자이크 생성 요청
  const handleGenerate = useCallback(async () => {
    if (!targetImageId) return;

    try {
      const job = await generateMosaic({
        session_id: sessionId,
        target_image_id: targetImageId,
        options: mosaicOptions,
      });

      updateJob(job);
      setStep('processing');
    } catch (err) {
      const message =
        err instanceof Error ? err.message : '모자이크 생성 요청 중 오류가 발생했습니다.';
      addToast('error', message);
    }
  }, [targetImageId, sessionId, mosaicOptions, updateJob, setStep, addToast]);

  return (
    <div className={styles.panel}>
      <h3 className={styles.title}>모자이크 설정</h3>

      {/* 타겟 미선택 경고 */}
      {!canGenerate && (
        <div className={styles.warning} role="alert">
          갤러리에서 타겟 이미지를 먼저 클릭하여 선택하세요.
        </div>
      )}

      {/* 격자 분할 수 */}
      <div className={styles.field}>
        <label className={styles.label} htmlFor="grid-division">
          격자 분할 수
          <span className={styles.value}>{mosaicOptions.grid_division}</span>
        </label>
        <input
          id="grid-division"
          type="range"
          min={10}
          max={200}
          step={5}
          value={mosaicOptions.grid_division}
          onChange={(e) => handleChange('grid_division', Number(e.target.value))}
          className={styles.range}
        />
        <div className={styles.rangeLabels}>
          <span>10 (적게)</span>
          <span>200 (많이)</span>
        </div>
      </div>

      {/* 타일 크기 */}
      <div className={styles.field}>
        <label className={styles.label} htmlFor="tile-size">
          타일 크기
        </label>
        <select
          id="tile-size"
          value={mosaicOptions.tile_size}
          onChange={(e) => handleChange('tile_size', Number(e.target.value))}
          className={styles.select}
        >
          {TILE_SIZE_OPTIONS.map((size) => (
            <option key={size} value={size}>
              {size}px
            </option>
          ))}
        </select>
      </div>

      {/* 색상 매칭 방법 */}
      <div className={styles.field}>
        <fieldset className={styles.fieldset}>
          <legend className={styles.label}>색상 매칭 방법</legend>
          <div className={styles.radioGroup}>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name="color-match"
                value="average"
                checked={mosaicOptions.color_match_method === 'average'}
                onChange={() => handleChange('color_match_method', 'average')}
                className={styles.radio}
              />
              평균색
            </label>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name="color-match"
                value="dominant"
                checked={mosaicOptions.color_match_method === 'dominant'}
                onChange={() => handleChange('color_match_method', 'dominant')}
                className={styles.radio}
              />
              주요색
            </label>
          </div>
        </fieldset>
      </div>

      {/* 타일 반복 허용 */}
      <div className={styles.field}>
        <div className={styles.toggleRow}>
          <label className={styles.label} htmlFor="allow-repeat">
            타일 이미지 반복 허용
          </label>
          <button
            id="allow-repeat"
            role="switch"
            aria-checked={mosaicOptions.allow_tile_repeat}
            className={`${styles.toggle} ${mosaicOptions.allow_tile_repeat ? styles.toggleOn : ''}`}
            onClick={() =>
              handleChange('allow_tile_repeat', !mosaicOptions.allow_tile_repeat)
            }
            type="button"
          >
            <span className={styles.toggleThumb} />
          </button>
        </div>
        <p className={styles.helpText}>
          비활성화 시 각 타일에 다른 이미지 사용 (이미지가 충분해야 함)
        </p>
      </div>

      {/* 블렌딩 강도 */}
      <div className={styles.field}>
        <label className={styles.label} htmlFor="blend-ratio">
          원본 블렌딩 강도
          <span className={styles.value}>
            {Math.round(mosaicOptions.blend_ratio * 100)}%
          </span>
        </label>
        <input
          id="blend-ratio"
          type="range"
          min={0}
          max={100}
          step={5}
          value={Math.round(mosaicOptions.blend_ratio * 100)}
          onChange={(e) =>
            handleChange('blend_ratio', Number(e.target.value) / 100)
          }
          className={styles.range}
        />
        <div className={styles.rangeLabels}>
          <span>0% (순수 모자이크)</span>
          <span>100% (원본)</span>
        </div>
      </div>

      {/* 출력 형식 */}
      <div className={styles.field}>
        <fieldset className={styles.fieldset}>
          <legend className={styles.label}>출력 파일 형식</legend>
          <div className={styles.radioGroup}>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name="output-format"
                value="png"
                checked={mosaicOptions.output_format === 'png'}
                onChange={() => handleChange('output_format', 'png')}
                className={styles.radio}
              />
              PNG (무손실)
            </label>
            <label className={styles.radioLabel}>
              <input
                type="radio"
                name="output-format"
                value="jpeg"
                checked={mosaicOptions.output_format === 'jpeg'}
                onChange={() => handleChange('output_format', 'jpeg')}
                className={styles.radio}
              />
              JPG (손실)
            </label>
          </div>
        </fieldset>
      </div>

      {/* JPG 품질 (JPG 선택 시에만 표시) */}
      {mosaicOptions.output_format === 'jpeg' && (
        <div className={styles.field}>
          <label className={styles.label} htmlFor="jpg-quality">
            JPG 품질
            <span className={styles.value}>{mosaicOptions.output_quality}</span>
          </label>
          <input
            id="jpg-quality"
            type="range"
            min={1}
            max={100}
            step={1}
            value={mosaicOptions.output_quality}
            onChange={(e) =>
              handleChange('output_quality', Number(e.target.value))
            }
            className={styles.range}
          />
          <div className={styles.rangeLabels}>
            <span>1 (저품질)</span>
            <span>100 (고품질)</span>
          </div>
        </div>
      )}

      {/* 생성 버튼 */}
      <button
        className={styles.generateButton}
        onClick={handleGenerate}
        disabled={!canGenerate}
        type="button"
      >
        {canGenerate ? '모자이크 생성' : '타겟 이미지를 먼저 선택하세요'}
      </button>
    </div>
  );
}
