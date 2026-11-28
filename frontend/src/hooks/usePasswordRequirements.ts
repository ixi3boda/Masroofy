import { useMemo, useState } from 'react';
import { Requirement, RequirementStatus } from '@components/molecules/RequirementList';
import { strings } from '@/strings';
import { getBrokenPasswordRules, PasswordRule } from '@/utils/validators';

const copy = strings.auth.passwordRequirements;
const RULES: PasswordRule[] = ['MIN_LENGTH', 'MAX_LENGTH', 'NUMBER_OR_SYMBOL', 'UPPERCASE'];

/**
 * The backend's password rules as a live checklist. Rules not met yet stay neutral while typing and turn red
 * after a submit attempt. Rules the server rejected stay red until the password changes.
 */
export function usePasswordRequirements(password: string) {
  const [showFailures, setShowFailures] = useState(false);
  const [serverResult, setServerResult] = useState<{ password: string; rules: string[] }>({ password: '', rules: [] });
  const broken = useMemo(() => getBrokenPasswordRules(password), [password]);
  const serverRules = serverResult.password === password ? serverResult.rules : [];

  const statusOf = (rule: PasswordRule): RequirementStatus => {
    if (serverRules.includes(rule)) return 'failed';
    if (!broken.includes(rule)) return 'met';
    return showFailures ? 'failed' : 'pending';
  };

  const requirements: Requirement[] = RULES.filter((rule) => rule !== 'MAX_LENGTH' || broken.includes(rule)).map(
    (rule) => ({ key: rule, label: copy[rule], status: statusOf(rule) })
  );

  return {
    requirements,
    /** Every rule passes. */
    isValid: broken.length === 0,
    /** Call on a submit attempt: rules still unmet turn red. */
    revealFailures: () => setShowFailures(true),
    /** The rule codes the server rejected for the password that was sent. */
    setServerFailures: (rules: string[]) => setServerResult({ password, rules }),
    /** Whether any server-rejected code is one of the checklist's rules. */
    isChecklistRule: (code: string) => (RULES as string[]).includes(code),
  };
}
