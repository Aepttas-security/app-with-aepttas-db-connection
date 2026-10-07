import { AppRegistry, Text, TextInput } from 'react-native';
import App from './App';
import { name as appName } from './app.json';

// Prevent unwanted OS display scaling from blowing up UI components
try {
  if (Text && Text.defaultProps != null) {
    Text.defaultProps.allowFontScaling = false;
  }
  if (TextInput && TextInput.defaultProps != null) {
    TextInput.defaultProps.allowFontScaling = false;
  }
} catch (e) {
  // Gracefully ignore on runtimes where defaultProps is frozen or deprecated
}

AppRegistry.registerComponent(appName, () => App);
