import React from 'react';
import { translateBrokerMessage } from './catalog.mjs';

const TRANSLATABLE_ATTRIBUTES = ['aria-label', 'placeholder', 'title', 'alt'];

function currentLocale() {
  try {
    return localStorage.getItem('luxline_language') || navigator.language || 'en';
  } catch {
    return 'en';
  }
}

function localizeTree(node, locale) {
  if (typeof node === 'string') return translateBrokerMessage(node, locale);
  if (Array.isArray(node)) return node.map((child) => localizeTree(child, locale));
  if (!React.isValidElement(node)) return node;

  const props = { ...node.props };
  for (const attribute of TRANSLATABLE_ATTRIBUTES) {
    if (typeof props[attribute] === 'string') props[attribute] = translateBrokerMessage(props[attribute], locale);
  }
  if (props.children !== undefined) props.children = localizeTree(props.children, locale);
  return React.cloneElement(node, props);
}

export function withBrokerTranslations(Component) {
  function TranslatedBrokerComponent(props) {
    return localizeTree(Component(props), currentLocale());
  }
  TranslatedBrokerComponent.displayName = `BrokerI18n(${Component.name || 'Screen'})`;
  return TranslatedBrokerComponent;
}
