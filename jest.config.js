module.exports = {
  verbose: true,
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/invenio_stats_dashboard/assets/'],
  moduleFileExtensions: ['js', 'jsx', 'json'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$':
      '<rootDir>/__mocks__/fileMock.js',
    '^@translations/invenio_stats_dashboard/i18next$': '<rootDir>/invenio_stats_dashboard/assets/semantic-ui/translations/invenio_stats_dashboard/i18next.js',
  },
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  transform: {
    '^.+\\.(js|jsx)$': 'babel-jest',
  },
  transformIgnorePatterns: [
    '/node_modules/(?!(react-invenio-forms|react-searchkit|axios|semantic-ui-react|@babel|@inveniosoftware)/)',
  ],
  testMatch: ['**/*.test.js?(x)', '**/*.spec.js?(x)'],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/tests_stats_dashboard/',
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
