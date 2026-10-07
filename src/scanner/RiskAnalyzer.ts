export interface AnalysisResult {
  riskScore: number;
  riskLevel: 'Low' | 'Medium' | 'High' | 'Critical';
  status: 'Safe' | 'Suspicious' | 'Malicious';
  threatType: 'spyware' | 'ransomware' | 'adware' | 'banker trojan' | 'executable threat' | 'script threat' | 'macro threat' | string | null;
  dangerousPermissions: string[];
  confidenceScore: number;
  recommendedAction: string;
}

const PERMISSION_WEIGHTS: Record<string, number> = {
  // Critical
  'android.permission.BIND_ACCESSIBILITY_SERVICE': 25,
  'android.permission.SYSTEM_ALERT_WINDOW': 25,
  'android.permission.SEND_SMS': 25,
  'android.permission.RECEIVE_SMS': 25,
  'android.permission.READ_SMS': 20,
  'android.permission.REQUEST_INSTALL_PACKAGES': 20,
  
  // High
  'android.permission.RECORD_AUDIO': 15,
  'android.permission.CAMERA': 15,
  'android.permission.ACCESS_FINE_LOCATION': 15,
  'android.permission.READ_CONTACTS': 12,
  'android.permission.READ_CALL_LOG': 12,
  'android.permission.PROCESS_OUTGOING_CALLS': 12,
  
  // Medium
  'android.permission.WRITE_EXTERNAL_STORAGE': 8,
  'android.permission.READ_EXTERNAL_STORAGE': 8,
  'android.permission.RECEIVE_BOOT_COMPLETED': 8,
  'android.permission.GET_TASKS': 8,
  
  // Low
  'android.permission.INTERNET': 3,
  'android.permission.ACCESS_NETWORK_STATE': 3,
  'android.permission.WAKE_LOCK': 2,
};

export const RiskAnalyzer = {
  analyzePermissions(permissions: string[]): AnalysisResult {
    // Filter to only dangerous permissions that we track
    const dangerousPermissions = permissions.filter(p => p in PERMISSION_WEIGHTS);
    
    // Sum weights
    const rawScore = dangerousPermissions.reduce((sum, p) => sum + (PERMISSION_WEIGHTS[p] || 0), 0);
    const riskScore = Math.min(rawScore, 100);

    // Status and Risk Level
    let status: 'Safe' | 'Suspicious' | 'Malicious';
    let riskLevel: 'Low' | 'Medium' | 'High' | 'Critical';

    if (riskScore >= 70) {
      status = 'Malicious';
      riskLevel = 'Critical';
    } else if (riskScore >= 45) {
      status = 'Malicious';
      riskLevel = 'High';
    } else if (riskScore >= 20) {
      status = 'Suspicious';
      riskLevel = 'Medium';
    } else {
      status = 'Safe';
      riskLevel = 'Low';
    }

    // Threat Type classification
    const threatType = this.detectThreatType(permissions, status);

    // Confidence Score (0.0 to 1.0)
    const confidenceScore = this.calculateConfidence(permissions, status, threatType, riskScore);

    // Recommended Action
    let recommendedAction = 'Safe. No action needed.';
    if (status === 'Malicious') {
      if (riskLevel === 'Critical') {
        recommendedAction = `Quarantine immediately! File matches a critical threat profile (${threatType}).`;
      } else {
        recommendedAction = 'Uninstall or Quarantine. This file requests high-risk permission structures.';
      }
    } else if (status === 'Suspicious') {
      const topPermissions = dangerousPermissions.slice(0, 3).map(p => p.substring(p.lastIndexOf('.') + 1));
      recommendedAction = `Monitor closely or Delete. Requests sensitive access: ${topPermissions.join(', ')}.`;
    }

    return {
      riskScore,
      riskLevel,
      status,
      threatType,
      dangerousPermissions,
      confidenceScore,
      recommendedAction,
    };
  },

  detectThreatType(permissions: string[], status: 'Safe' | 'Suspicious' | 'Malicious'): AnalysisResult['threatType'] {
    if (status === 'Safe') return null;

    const hasSms = permissions.some(p => p.toUpperCase().includes('SMS'));
    const hasOverlay = permissions.includes('android.permission.SYSTEM_ALERT_WINDOW');
    const hasAccessibility = permissions.includes('android.permission.BIND_ACCESSIBILITY_SERVICE');
    const hasStorage = permissions.includes('android.permission.WRITE_EXTERNAL_STORAGE');
    const hasBoot = permissions.includes('android.permission.RECEIVE_BOOT_COMPLETED');

    const privacyCount = [
      'android.permission.RECORD_AUDIO',
      'android.permission.CAMERA',
      'android.permission.ACCESS_FINE_LOCATION',
      'android.permission.READ_CONTACTS',
      'android.permission.READ_CALL_LOG',
    ].filter(p => permissions.includes(p)).length;

    // 1. Banker Trojan Signature
    if ((hasSms && (hasOverlay || hasAccessibility)) || (hasAccessibility && hasOverlay)) {
      return 'banker trojan';
    }

    // 2. Ransomware Signature
    if (hasOverlay && hasStorage && hasBoot) {
      return 'ransomware';
    }

    // 3. Spyware Signature
    if (privacyCount >= 3) {
      return 'spyware';
    }

    // 4. Adware Signature
    if (
      permissions.includes('android.permission.INTERNET') &&
      permissions.includes('android.permission.ACCESS_NETWORK_STATE') &&
      (hasOverlay || permissions.includes('android.permission.WAKE_LOCK'))
    ) {
      return 'adware';
    }

    return status === 'Malicious' ? 'banker trojan' : 'adware';
  },

  calculateConfidence(permissions: string[], status: string, threatType: string | null, riskScore: number): number {
    if (status === 'Safe') {
      if (permissions.length === 0) return 0.98;
      return 0.92;
    }

    let confidence = 0.75; // Base
    if (threatType) {
      confidence += 0.10;
    }
    confidence += (riskScore / 1000.0);

    return Math.min(confidence, 0.96);
  }
};
