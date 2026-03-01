import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.voidfill.app',
  appName: 'VoidFill',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
    url: 'https://void-fill-production.up.railway.app',
  },
};

export default config;
