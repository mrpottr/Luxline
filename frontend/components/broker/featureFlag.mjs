export function isBrokerPanelEnabled(value) {
  return value === 'true';
}

export function canShowBrokerNavigation(flagValue, role) {
  return isBrokerPanelEnabled(flagValue) && ['business_account', 'broker_account'].includes(role);
}
