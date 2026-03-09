module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'body-max-line-length': [0, 'always', Infinity],
    'type-empty': [0, 'always'],
    'subject-empty': [0, 'always']
  }
};
