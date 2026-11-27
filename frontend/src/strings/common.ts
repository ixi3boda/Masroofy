/** Copy shared across screens and reusable components. */
export const commonStrings = {
  appName: 'Masroofy',
  genericError: 'Something went wrong. Try again.',
  backToLogin: 'Back to log in',
  resendCode: 'Resend code',
  resendCodeIn: (seconds: number) => `Resend code in ${seconds}s`,
  selected: 'Selected',
  linkArrow: (label: string) => `${label} →`,

  fields: {
    emailLabel: 'Email address',
    emailPlaceholder: 'Enter your email',
    passwordLabel: 'Password',
  },

  a11y: {
    goBack: 'Go back',
    dismiss: 'Dismiss',
    profile: 'Profile',
    takePhoto: 'Take photo',
    startRecording: 'Start recording',
    stopRecording: 'Stop recording',
    searchFor: (query: string) => `Search for ${query}`,
    plannedMonths: (months: string[]) => `Planned months: ${months.join(', ')}`,
    receipt: (merchant: string, date: string, time: string, total: string) =>
      `Receipt from ${merchant}, ${date} ${time}, total ${total}`,
  },

  tabs: {
    home: 'Home',
    savings: 'Savings',
    reminders: 'Reminders',
    settings: 'Settings',
    add: 'Add transaction',
  },

  capture: {
    retake: 'Retake',
    flashOff: 'Flash off',
  },

  dateRange: {
    title: 'Date range',
    from: 'From',
    to: 'To',
  },

  transcript: {
    title: 'Editable transcript',
    fieldLabel: 'Transcript words',
  },

  profile: {
    edit: 'Edit profile',
  },
};
