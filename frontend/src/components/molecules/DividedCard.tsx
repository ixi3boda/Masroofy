import React, { Children, Fragment, ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Divider from '@components/atoms/Divider';

export interface DividedCardProps {
  title?: string;
  /** Small line under the title, e.g. "28 Oct 2026 · 14:32 · Read-only". */
  subtitle?: string;
  /** Rendered under the title without a divider, e.g. a status chip or warning banner. */
  header?: ReactNode;
  /** Each child is separated from the next by a divider; `null` children are skipped. */
  children: ReactNode;
  /** Closing note under the last row, without a divider. */
  footnote?: string;
  /** Very last, under the footnote, e.g. the card's button. */
  action?: ReactNode;
  style?: StyleProp<ViewStyle>;
}

/**
 * Card of stacked rows separated by dividers — settings groups, detail
 * summaries, reminder lists, comparison breakdowns, processing steps.
 */
const DividedCard: React.FC<DividedCardProps> = ({ title, subtitle, header, children, footnote, action, style }) => {
  const rows = Children.toArray(children);

  return (
    <Card style={[styles.card, style]}>
      {title || subtitle ? (
        <View style={styles.heading}>
          {title ? <AppText variant="subheading16">{title}</AppText> : null}
          {subtitle ? (
            <AppText variant="body12" color={colors.text.secondary}>
              {subtitle}
            </AppText>
          ) : null}
        </View>
      ) : null}
      {header}
      {rows.map((row, index) => (
        // Children.toArray assigns stable keys; this wrapper keeps them with each divider.
        <Fragment key={(row as { key?: string }).key ?? index}>
          {index > 0 ? <Divider /> : null}
          {row}
        </Fragment>
      ))}
      {footnote ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {footnote}
        </AppText>
      ) : null}
      {action}
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { gap: 14 },
  heading: { gap: 4 },
});

export default DividedCard;
