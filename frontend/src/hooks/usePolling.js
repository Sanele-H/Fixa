import { useEffect, useRef } from "react";

import { POLLING_INTERVAL_IN_MILLISECONDS } from "../constants.js";

/**
 * Calls `loadData` now and then every `intervalInMilliseconds` until the component unmounts.
 * Errors are logged, not thrown, so one failed poll on bad Wi-Fi doesn't break the screen.
 * The latest `loadData` is always used, so it may close over changing state.
 */
export default function usePolling(loadData, intervalInMilliseconds = POLLING_INTERVAL_IN_MILLISECONDS) {
  const latestLoadDataRef = useRef(loadData);
  latestLoadDataRef.current = loadData;

  useEffect(() => {
    const runLoadData = () => Promise.resolve(latestLoadDataRef.current()).catch(console.error);
    runLoadData();
    const intervalId = setInterval(runLoadData, intervalInMilliseconds);
    return () => clearInterval(intervalId);
  }, [intervalInMilliseconds]);
}
