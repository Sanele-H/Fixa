import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { JOB_STATE_ORDER, type JobState } from "../api/types";
import { Chip } from "../ui";

/** Class for one step: done (before the current one), current, or still to come. */
function buildStepClassName(stepIndex: number, currentIndex: number) {
  if (stepIndex === currentIndex) {
    return "state-ruler__step state-ruler__step--current";
  }
  return stepIndex < currentIndex ? "state-ruler__step state-ruler__step--done" : "state-ruler__step";
}

/**
 * Where a job is, drawn like the time-zone ruler in the design: every state along a line,
 * with a tall mark over the current one. The ruler scrolls sideways and starts centred on
 * the current state. A cancelled job shows a single chip instead.
 */
export function JobStateRuler({ state }: { state: JobState }) {
  const { t } = useTranslation();
  const rulerRef = useRef<HTMLOListElement>(null);
  const currentIndex = JOB_STATE_ORDER.indexOf(state);

  useEffect(() => {
    const ruler = rulerRef.current;
    const currentStep = ruler?.querySelector<HTMLElement>("[aria-current]");
    if (ruler && currentStep) {
      ruler.scrollLeft = currentStep.offsetLeft - (ruler.clientWidth - currentStep.offsetWidth) / 2;
    }
  }, [currentIndex]);

  if (state === "cancelled") {
    return <Chip tone="outline">{t("jobState.cancelled")}</Chip>;
  }
  return (
    <ol ref={rulerRef} className="state-ruler" aria-label={t("job.progress")}>
      {JOB_STATE_ORDER.map((step, stepIndex) => (
        <li
          key={step}
          className={buildStepClassName(stepIndex, currentIndex)}
          aria-current={stepIndex === currentIndex ? "step" : undefined}
        >
          {t(`jobState.${step}`)}
        </li>
      ))}
    </ol>
  );
}
