import test from 'node:test';
import assert from 'node:assert/strict';

import { canShowBrokerNavigation, isBrokerPanelEnabled } from '../components/broker/featureFlag.mjs';
import { resolveBrokerLocale, translateBrokerMessage } from '../components/broker/i18n/catalog.mjs';

test('broker panel flag is off unless explicitly set to true', () => {
  assert.equal(isBrokerPanelEnabled(undefined), false);
  assert.equal(isBrokerPanelEnabled('false'), false);
  assert.equal(isBrokerPanelEnabled('true'), true);
});

test('broker navigation requires the flag and a business account role', () => {
  assert.equal(canShowBrokerNavigation('true', 'business_account'), true);
  assert.equal(canShowBrokerNavigation('true', 'broker_account'), true);
  assert.equal(canShowBrokerNavigation('false', 'business_account'), false);
  assert.equal(canShowBrokerNavigation('false', 'broker_account'), false);
  assert.equal(canShowBrokerNavigation('true', 'standard_user'), false);
});

test('broker namespace catalogs resolve English, Sinhala and Tamil locales', () => {
  assert.equal(resolveBrokerLocale('si-LK'), 'si');
  assert.equal(resolveBrokerLocale('ta'), 'ta');
  assert.equal(resolveBrokerLocale('fr'), 'en');
  assert.equal(translateBrokerMessage('Dashboard', 'si'), 'උපකරණ පුවරුව');
  assert.equal(translateBrokerMessage('Dashboard', 'ta'), 'முகப்புப் பலகை');
  assert.equal(translateBrokerMessage('Unknown phrase', 'ta'), 'Unknown phrase');
});
