import { DefaultTheme } from 'react-native-paper';

export const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#6200ee',
    primaryContainer: '#e8def8',
    secondary: '#03dac6',
    secondaryContainer: '#a4f7cf',
    tertiary: '#bb86fc',
    surface: '#ffffff',
    surfaceVariant: '#f3f3f3',
    background: '#fefefe',
    error: '#b00020',
    errorContainer: '#fcd8df',
    onPrimary: '#ffffff',
    onSecondary: '#000000',
    onSurface: '#1a1a1a',
    onSurfaceVariant: '#666666',
    onError: '#ffffff',
    outline: '#e0e0e0',
    shadow: '#000000',
    inverseSurface: '#2d2d2d',
    inverseOnSurface: '#f1f1f1',
    inversePrimary: '#bb86fc',
    // Custom colors for CrackPi
    success: '#4caf50',
    warning: '#ff9800',
    info: '#2196f3',
    onSuccess: '#ffffff',
    onWarning: '#ffffff',
    onInfo: '#ffffff',
    // Status colors
    online: '#4caf50',
    offline: '#f44336',
    working: '#2196f3',
    idle: '#ff9800',
    failed: '#f44336',
    completed: '#4caf50',
    pending: '#ff9800',
    // Node health colors
    healthy: '#4caf50',
    degraded: '#ff9800',
    critical: '#f44336',
  },
  roundness: 8,
  fonts: {
    ...DefaultTheme.fonts,
    regular: {
      fontFamily: 'System',
      fontWeight: '400',
    },
    medium: {
      fontFamily: 'System',
      fontWeight: '500',
    },
    light: {
      fontFamily: 'System',
      fontWeight: '300',
    },
    thin: {
      fontFamily: 'System',
      fontWeight: '100',
    },
  },
};

export const darkTheme = {
  ...theme,
  dark: true,
  colors: {
    ...theme.colors,
    primary: '#bb86fc',
    primaryContainer: '#4a2d6b',
    secondary: '#03dac6',
    secondaryContainer: '#005047',
    surface: '#121212',
    surfaceVariant: '#1e1e1e',
    background: '#000000',
    onPrimary: '#000000',
    onSecondary: '#000000',
    onSurface: '#ffffff',
    onSurfaceVariant: '#cccccc',
    outline: '#2d2d2d',
    inverseSurface: '#e6e6e6',
    inverseOnSurface: '#1a1a1a',
    inversePrimary: '#6200ee',
  },
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const typography = {
  h1: {
    fontSize: 32,
    fontWeight: 'bold',
    lineHeight: 40,
  },
  h2: {
    fontSize: 28,
    fontWeight: 'bold',
    lineHeight: 36,
  },
  h3: {
    fontSize: 24,
    fontWeight: 'bold',
    lineHeight: 32,
  },
  h4: {
    fontSize: 20,
    fontWeight: 'bold',
    lineHeight: 28,
  },
  h5: {
    fontSize: 18,
    fontWeight: '600',
    lineHeight: 24,
  },
  h6: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 22,
  },
  body1: {
    fontSize: 16,
    fontWeight: '400',
    lineHeight: 24,
  },
  body2: {
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 20,
  },
  caption: {
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 16,
  },
  overline: {
    fontSize: 10,
    fontWeight: '500',
    lineHeight: 16,
    textTransform: 'uppercase',
    letterSpacing: 1.5,
  },
};

export const shadows = {
  small: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.18,
    shadowRadius: 1.0,
    elevation: 1,
  },
  medium: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  large: {
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.30,
    shadowRadius: 4.65,
    elevation: 8,
  },
};

export const animations = {
  short: 200,
  medium: 300,
  long: 500,
};

export const breakpoints = {
  phone: 0,
  tablet: 768,
  desktop: 1024,
};

// Component-specific themes
export const cardTheme = {
  elevation: 2,
  borderRadius: theme.roundness,
  backgroundColor: theme.colors.surface,
  padding: spacing.md,
};

export const buttonTheme = {
  borderRadius: theme.roundness,
  paddingHorizontal: spacing.md,
  paddingVertical: spacing.sm,
};

export const inputTheme = {
  borderRadius: theme.roundness,
  borderWidth: 1,
  borderColor: theme.colors.outline,
  paddingHorizontal: spacing.md,
  paddingVertical: spacing.sm,
};

// Status-specific styles
export const statusStyles = {
  online: {
    backgroundColor: theme.colors.online,
    color: theme.colors.onSuccess,
  },
  offline: {
    backgroundColor: theme.colors.offline,
    color: theme.colors.onError,
  },
  working: {
    backgroundColor: theme.colors.working,
    color: theme.colors.onInfo,
  },
  idle: {
    backgroundColor: theme.colors.idle,
    color: theme.colors.onWarning,
  },
  failed: {
    backgroundColor: theme.colors.failed,
    color: theme.colors.onError,
  },
  completed: {
    backgroundColor: theme.colors.completed,
    color: theme.colors.onSuccess,
  },
  pending: {
    backgroundColor: theme.colors.pending,
    color: theme.colors.onWarning,
  },
};

export default theme;