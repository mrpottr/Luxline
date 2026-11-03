export function isBrokerPanelEnabled(value) {
  return value === 'true';
}

export function canShowBrokerNavigation(flagValue, role) {
  return isBrokerPanelEnabled(flagValue) && role === 'business_account';
}
