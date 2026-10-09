import { telemetryService } from './TelemetryService';
import { Storage } from '../utils/storage';

class ChildDaemonService {
  private isRunning = false;

  /**
   * Start background telemetry worker (GPS telemetry every 30s, app usage sync every 60s)
   */
  startDaemon(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    console.log('[ChildDaemon] 🚀 Starting child background telemetry daemon...');
    telemetryService.start();
  }

  stopDaemon(): void {
    this.isRunning = false;
    telemetryService.stop();
    console.log('[ChildDaemon] 🛑 Stopped child background telemetry daemon.');
  }

  /**
   * Trigger an immediate single telemetry ping
   */
  async triggerImmediateTick(): Promise<void> {
    await telemetryService.sendLocationTick();
    await telemetryService.sendAppsUsageTick();
  }
}

export const ChildDaemon = new ChildDaemonService();
export default ChildDaemon;
