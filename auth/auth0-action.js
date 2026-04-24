exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://mycorp.example';
  const roles = event.authorization && Array.isArray(event.authorization.roles)
    ? event.authorization.roles
    : [];

  api.accessToken.setCustomClaim(`${namespace}/roles`, roles);
};
