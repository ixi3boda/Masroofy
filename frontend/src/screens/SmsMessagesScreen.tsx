import React from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import Chip from '@components/atoms/Chip';
import SegmentedControl from '@components/atoms/SegmentedControl';
import TabPanel from '@components/atoms/TabPanel';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ListRow from '@components/molecules/ListRow';
import SectionHeader from '@components/molecules/SectionHeader';
import StateSummary from '@components/molecules/StateSummary';
import BankMessageCard from '@components/organisms/BankMessageCard';
import BottomTabBar from '@components/organisms/BottomTabBar';
import ScreenLayout from '@components/templates/ScreenLayout';
import { whenOpen } from '@/constants/features';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useServiceData } from '@/hooks/useServiceData';
import { useTabParam } from '@/hooks/useTabParam';
import { ROUTES } from '@/navigation/routes';
import { dashboardService } from '@/services/dashboardService';
import { smsService } from '@/services/smsService';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { BankMessage } from '@/types/sms';
import { formatCurrency, formatDateTime, formatMonthName } from '@/utils/formatters';

const TAB_ORDER = ['new', 'reviewed'] as const;

const copy = strings.sms.messages;

const openImport = () => router.push(ROUTES.sms.import);
const openReview = (id: string) => router.push({ pathname: ROUTES.sms.processing, params: { id } });
const openAdd = whenOpen('transactions', () => router.push(ROUTES.transactions.add));
const openTransaction = (id: string) => router.push({ pathname: ROUTES.transactions.details, params: { id } });
const goHome = () => router.dismissTo(ROUTES.app.home);

/** "NBE", "NBE and Banque Misr", "CIB, NBE and Banque Misr" */
const joinNames = (names: string[]) =>
  names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}` : names.join('');

/** Status chip and hint for a message still waiting in the "Still new" list. */
const pendingSummary = (message: BankMessage) => {
  if (message.kind === 'withdrawal') return { label: copy.statusWithdrawal, meta: copy.metaWithdrawal };
  if (message.match) return { label: copy.statusMatch, meta: copy.metaMatch(message.match.merchant) };
  return { label: copy.statusUnmatched, meta: copy.metaUnmatched(message.merchant ?? message.bank) };
};

interface TabProps {
  newMessages: BankMessage[];
  reviewedMessages: BankMessage[];
}

/** 04-02: every message still waiting for review. */
const NewTab: React.FC<TabProps> = ({ newMessages }) => {
  const unmatchedBanks = newMessages.filter((message) => !message.match).map((message) => message.bank);

  return (
    <>
      <FeedbackBanner icon="shield-check" title={copy.guidanceTitle} message={copy.guidanceMessage} />
      <AppText variant="body12" color={colors.text.secondary}>
        {copy.listCaption}
      </AppText>
      {newMessages.length === 0 ? (
        <Card>
          <StateSummary size="compact" icon="sms" heading={copy.emptyNewTitle} description={copy.emptyNewMessage} />
        </Card>
      ) : null}
      {newMessages.map((message) => (
        <BankMessageCard
          key={message.id}
          bank={message.bank}
          receivedAt={formatDateTime(message.receivedAt)}
          amount={formatCurrency(message.amount)}
          body={message.body}
          notice={
            message.match ? (
              <FeedbackBanner
                tone="warning"
                icon="copy-check"
                title={copy.duplicateTitle}
                message={copy.duplicateMessage(message.match.merchant)}
              />
            ) : null
          }
          status={{ label: copy.newChip, tone: 'info' }}
          actionLabel={copy.reviewMessage}
          onAction={() => openReview(message.id)}
        />
      ))}
      {unmatchedBanks.length > 0 ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.newFootnote(joinNames(unmatchedBanks))}
        </AppText>
      ) : null}
    </>
  );
};

/** 04-09: what was already linked, then the messages that are still new. */
const ReviewedTab: React.FC<TabProps> = ({ newMessages, reviewedMessages }) => {
  const { totalExpense, primaryAccount, cashBalance } = dashboardService.getSummary();
  const latest = reviewedMessages[0];

  return (
    <>
      {latest?.match ? (
        <FeedbackBanner
          tone="success"
          title={copy.reviewedTitle(latest.bank)}
          message={copy.reviewedMessage(latest.match.merchant)}
        />
      ) : null}
      {reviewedMessages.length === 0 ? (
        <Card>
          <StateSummary
            size="compact"
            icon="circle-check"
            heading={copy.emptyReviewedTitle}
            description={copy.emptyReviewedMessage}
          />
        </Card>
      ) : null}
      {reviewedMessages.map(({ id, bank, match, receivedAt, amount, body }) =>
        match ? (
          <Card key={id}>
            <Chip label={copy.reviewedChip} tone="success" />
            <ListRow
              title={copy.reviewedRowTitle(bank, match.merchant)}
              subtitle={formatDateTime(receivedAt)}
              trailing={formatCurrency(amount)}
            />
            <AppText variant="body14" color={colors.text.secondary}>
              {body}
            </AppText>
            <AppText variant="body12" color={colors.text.secondary}>
              {copy.reviewedMeta(strings.categories[match.category], match.account.shortLabel)}
            </AppText>
            {transactionService.getTransaction(match.transactionId) ? (
              <Button
                title={copy.viewTransaction}
                variant="outline"
                onPress={whenOpen('transactions', () => openTransaction(match.transactionId))}
              />
            ) : null}
          </Card>
        ) : null,
      )}
      {newMessages.length > 0 ? (
        <>
          <SectionHeader title={copy.stillNew(newMessages.length)} />
          <DividedCard>
            {newMessages.map((message) => {
              const { label, meta } = pendingSummary(message);
              return (
                <ListRow
                  key={message.id}
                  title={message.bank}
                  subtitle={formatDateTime(message.receivedAt)}
                  trailing={formatCurrency(message.amount)}
                  status={{ label, tone: 'info' }}
                  meta={meta}
                  onPress={() => openReview(message.id)}
                />
              );
            })}
          </DividedCard>
          <AppText variant="body12" color={colors.text.secondary}>
            {copy.reviewedFootnote(
              formatMonthName(newMessages[0].receivedAt),
              formatCurrency(totalExpense),
              formatCurrency(primaryAccount.balance + cashBalance),
            )}
          </AppText>
        </>
      ) : null}
    </>
  );
};

/**
 * 04-02 / 04-09 · Bank Messages: imported SMS split into "New" and "Reviewed".
 * The tabs stay pinned under the header; switching slides the list in from the chosen tab's side.
 */
const SmsMessagesScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.app.home);
  const [tab, changeTab] = useTabParam(TAB_ORDER);
  // Statuses change on the review screens; re-read whenever the list is shown again.
  const messages = useServiceData(smsService.getMessages);

  const newMessages = messages.filter((message) => message.status === 'new');
  const reviewedMessages = messages.filter((message) => message.status === 'reviewed');

  const tabProps = { newMessages, reviewedMessages };

  // Same header, tabs, footer and tab bar on both tabs: only the list in between changes.
  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      toolbar={
        <SegmentedControl
          options={[
            { value: 'new', label: copy.tabNew(newMessages.length) },
            { value: 'reviewed', label: copy.tabReviewed(reviewedMessages.length) },
          ]}
          value={tab}
          onChange={changeTab}
        />
      }
      scrollKey={tab}
      footer={<Button title={copy.importButton} onPress={openImport} />}
      bottomBar={
        <BottomTabBar
          activeTab="home"
          onAddPress={openAdd}
          onTabPress={(key) => {
            if (key === 'home') goHome();
          }}
        />
      }
    >
      <TabPanel index={TAB_ORDER.indexOf(tab)}>
        {tab === 'new' ? <NewTab {...tabProps} /> : <ReviewedTab {...tabProps} />}
      </TabPanel>
    </ScreenLayout>
  );
};

export default SmsMessagesScreen;
