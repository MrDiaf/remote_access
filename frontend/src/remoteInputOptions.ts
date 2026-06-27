export const defaultRemoteInput = {
  local_keyboard_layout: 'auto',
  remote_keyboard_layout: 'en-us-qwerty',
  capture_release_shortcut: 'escape'
};

export const localKeyboardLayoutOptions = [
  { value: 'auto', label: 'Auto' },
  { value: 'en-us-qwerty', label: 'English US' },
  { value: 'en-gb-qwerty', label: 'English UK' },
  { value: 'sv-se-qwerty', label: 'Swedish' },
  { value: 'da-dk-qwerty', label: 'Danish' },
  { value: 'no-no-qwerty', label: 'Norwegian' },
  { value: 'fi-fi-qwerty', label: 'Finnish' },
  { value: 'de-de-qwertz', label: 'German' },
  { value: 'de-ch-qwertz', label: 'Swiss German' },
  { value: 'fr-fr-azerty', label: 'French' },
  { value: 'fr-be-azerty', label: 'Belgian French' },
  { value: 'fr-ch-qwertz', label: 'Swiss French' },
  { value: 'es-es-qwerty', label: 'Spanish' },
  { value: 'es-latam-qwerty', label: 'Spanish Latin American' },
  { value: 'it-it-qwerty', label: 'Italian' },
  { value: 'pt-br-qwerty', label: 'Portuguese Brazilian' },
  { value: 'hu-hu-qwertz', label: 'Hungarian' },
  { value: 'ja-jp-qwerty', label: 'Japanese' },
  { value: 'tr-tr-qwerty', label: 'Turkish Q' }
];

export const remoteKeyboardLayoutOptions = [
  ...localKeyboardLayoutOptions.filter((option) => option.value !== 'auto'),
  { value: 'failsafe', label: 'Failsafe Unicode' }
];

export const captureReleaseOptions = [
  { value: 'escape', label: 'Escape' },
  { value: 'ctrl-alt', label: 'Ctrl + Alt' },
  { value: 'ctrl-shift', label: 'Ctrl + Shift' },
  { value: 'manual', label: 'Manual release only' }
];

export function optionLabel(options: Array<{ value: string; label: string }>, value: string) {
  return options.find((option) => option.value === value)?.label || value;
}
