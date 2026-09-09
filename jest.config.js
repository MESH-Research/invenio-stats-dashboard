module.exports = {
  verbose: false,
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/invenio_stats_dashboard/assets/'],
  moduleFileExtensions: ['js', 'jsx', 'json'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$':
      '<rootDir>/__mocks__/fileMock.js',
    '^@translations/invenio_stats_dashboard/i18next$': '<rootDir>/invenio_stats_dashboard/assets/semantic-ui/translations/invenio_stats_dashboard/i18next.js',
    // Prefer this package's install over nested translation/node_modules trees.
    '^i18next$': '<rootDir>/node_modules/i18next',
    '^i18next-browser-languagedetector$':
      '<rootDir>/node_modules/i18next-browser-languagedetector',
    '^react-i18next$': '<rootDir>/node_modules/react-i18next',
    '^react$': '<rootDir>/node_modules/react',
    '^react-dom$': '<rootDir>/node_modules/react-dom',
    '^echarts-for-react$': '<rootDir>/node_modules/echarts-for-react',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: [
    // pnpm: allowlist must match the package after the optional
    // .pnpm/<pkg>@ver/node_modules/ prefix (see root jest.config.js).
    '/node_modules/(?!(?:\\.pnpm/[^/]+/node_modules/)?(react-invenio-forms|react-searchkit|axios|semantic-ui-react|echarts-for-react|@babel|@inveniosoftware)(/|$))',
  ],
  testMatch: ['**/*.test.js?(x)', '**/*.spec.js?(x)'],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/tests/',
  ],
  collectCoverageFrom: [
    'invenio_stats_dashboard/assets/**/*.{js,jsx}',
    '!**/node_modules/**',
    '!**/*.test.{js,jsx}',
    '!**/*.spec.{js,jsx}',
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov'],
  resetMocks: true,
  restoreMocks: true,
};
