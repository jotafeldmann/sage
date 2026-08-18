import { ApolloClient, HttpLink, InMemoryCache } from "@apollo/client";

/**
 * Points at a relative /graphql endpoint. There is no real server: MSW
 * intercepts the request in the browser and in tests.
 */
export function createApolloClient() {
  return new ApolloClient({
    link: new HttpLink({ uri: "/graphql" }),
    cache: new InMemoryCache(),
  });
}
