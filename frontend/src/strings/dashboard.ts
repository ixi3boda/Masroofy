/** Copy for the "02 / Home Dashboard" screen and its sections. */
export const dashboardStrings = {
  title: 'Masroofy Home',
  totalSalary: 'Total Salary',
  totalExpense: 'Total Expense',
  currentBalance: 'Current Balance',
  cashBalance: (amount: string) => `Cash · ${amount}`,

  moreActions: {
    title: 'More Actions',
    savings: 'Savings',
    reminders: 'Reminders',
    insights: 'Insights',
    budgets: 'Budgets',
    markets: 'Markets',
    accounts: 'Accounts',
    salarySetup: 'Salary Setup',
  },

  quickActions: {
    title: 'Quick Actions',
    addTransaction: 'Add Transaction',
    smsDetection: 'SMS Detection',
    scanReceipt: 'Scan Receipt',
    voiceEntry: 'Voice Entry',
  },

  budget: {
    title: 'Budget Progress',
    used: (percent: number) => `${percent}% Used`,
    remaining: 'Remaining Allowance',
    caption: (period: string, limit: string) => `${period} • Budget ${limit}`,
  },

  incomeVsExpenses: {
    title: 'Income vs Expenses',
    income: 'Income',
    expenses: 'Expenses',
    caption: (period: string) => `${period} • Income vs Expenses`,
  },

  recentTransactions: {
    title: 'Recent Transactions',
    viewAll: 'View All',
  },
};
