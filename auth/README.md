# Auth0 Setup

This project uses Auth0 as the identity provider and treats the backend as the only trust boundary.

## Create the Auth0 API

1. Create a new API in the Auth0 dashboard.
2. Set the identifier to the backend audience, for example `https://api.mycorp.example`.
3. Use `RS256` signing.

## Create the SPA application

1. Create a Single Page Application.
2. Add `http://localhost:5173` to the allowed callback URLs.
3. Add `http://localhost:5173` to allowed logout URLs and web origins.
4. Set the audience to the API identifier.

## Define roles

Create these roles at minimum:

1. `HR_Manager`
2. `Intern`
3. `Admin`

Assign roles to users in the Auth0 dashboard.

## Add the roles claim

Use an Auth0 Action to inject the namespaced roles claim into the access token.

The action code is in [auth0-action.js](auth0-action.js).

Use the namespace:

`https://mycorp.example/roles`

## Notes

The frontend never authorizes access by itself. It only obtains an access token and sends it to the backend.
