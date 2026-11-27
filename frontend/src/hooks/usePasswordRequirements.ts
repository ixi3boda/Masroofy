import { useMemo, useState } from 'react';
import { Requirement, RequirementStatus } from '@components/molecules/RequirementList';
import { strings } from '@/strings';
import { getBrokenPasswordRules, PasswordPersonalInfo, PasswordRule } from '@/utils/validators';

const copy = strings.auth.passwordRequirements;
const RULES: PasswordRule[] = ['MIN_LENGTH', 'MAX_LENGTH', 'NUMBER_OR_SYMBOL', 'NO_PERSONAL_INFO', 'COMMON_PASSWORD'];

interface Options {
  personal: PasswordPersonalInfo;
  /** Both name and email are known here, so passing NO_PERSONAL_INFO can show as met (the backend checks both). */
  personalInfoComplete: boolean;
}

/**
 * The backend's password rules as a live checklist. Rules not met yet stay neutral while typing and turn red
 * after a submit attempt; a name or email in the password turns red at once. Rules the server rejected stay
 * red until the password changes.
 */
export function usePasswordRequirements(password: string, { personal, personalInfoComplete }: Options) {
  const [showFailures, setShowFailures] = useState(false);
  const [serverResult, setServerResult] = useState<{ password: string; rules: string[] }>({ password: '', rules: [] });
  const { fullName, email } = personal;
  const broken = useMemo(() => getBrokenPasswordRules(password, { fullName, email }), [password, fullName, email]);
  const serverRules = serverResult.password === password ? serverResult.rules : [];

  const statusOf = (rule: PasswordRule): RequirementStatus => {
    if (serverRules.includes(rule)) return 'failed';
    if (rule === 'COMMON_PASSWORD') return 'pending';
    const isBroken = broken.includes(rule);
    if (rule === 'NO_PERSONAL_INFO') {
      if (isBroken) return 'failed';
      return password && personalInfoComplete ? 'met' : 'pending';
    }
    if (!isBroken) return 'met';
    return showFailures ? 'failed' : 'pending';
  };

  const requirements: Requirement[] = RULES.filter((rule) => rule !== 'MAX_LENGTH' || broken.includes(rule)).map(
    (rule) => ({ key: rule, label: copy[rule], status: statusOf(rule) })
  );

  return {
    requirements,
    /** Every rule this device can check passes (COMMON_PASSWORD is left to the server). */
    isValid: broken.length === 0,
    /** Call on a submit attempt: rules still unmet turn red. */
    revealFailures: () => setShowFailures(true),
    /** The rule codes the server rejected for the password that was sent. */
    setServerFailures: (rules: string[]) => setServerResult({ password, rules }),
    /** Whether any server-rejected code is one of the checklist's rules. */
    isChecklistRule: (code: string) => (RULES as string[]).includes(code),
  };
}
