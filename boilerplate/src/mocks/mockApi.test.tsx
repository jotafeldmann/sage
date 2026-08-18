/**
 * Smoke test for the mock API wiring itself, not for any application feature.
 *
 * It exists so that a broken Apollo/MSW setup fails here, loudly and in one
 * place, rather than surfacing as a confusing failure in whatever feature is
 * built on top of it.
 */
import { ApolloProvider, useMutation, useQuery } from "@apollo/client/react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createApolloClient } from "../apollo/client";
import {
  ADD_CAR,
  type AddCarData,
  type AddCarVariables,
  GET_CARS,
  type GetCarsData,
} from "../graphql/operations";

function CarList() {
  const { data, loading, error } = useQuery<GetCarsData>(GET_CARS);
  const [addCar] = useMutation<AddCarData, AddCarVariables>(ADD_CAR, {
    refetchQueries: [{ query: GET_CARS }],
  });

  if (loading) return <p>Loading</p>;
  if (error) return <p>{`Error: ${error.message}`}</p>;

  return (
    <>
      <button
        onClick={() =>
          void addCar({
            variables: {
              input: {
                make: "Mazda",
                model: "MX-5",
                year: 2020,
                color: "Green",
                mobile: "m",
                tablet: "t",
                desktop: "d",
              },
            },
          })
        }
      >
        Add
      </button>
      <ul>
        {data?.cars.map((car) => (
          <li key={car.id}>{`${car.make} ${car.model} ${car.year} ${car.color}`}</li>
        ))}
      </ul>
    </>
  );
}

function renderList() {
  render(
    <ApolloProvider client={createApolloClient()}>
      <CarList />
    </ApolloProvider>,
  );
}

describe("mock GraphQL API", () => {
  it("serves the five seed cars through the GetCars query", async () => {
    renderList();

    expect(await screen.findByText("Ford Mustang 2023 Red")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
  });

  it("adds a car through the AddCar mutation", async () => {
    renderList();
    await screen.findByText("Ford Mustang 2023 Red");

    await userEvent.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText("Mazda MX-5 2020 Green")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(6);
  });

  it("isolates each test from the previous one's mutations", async () => {
    renderList();

    expect(await screen.findByText("Ford Mustang 2023 Red")).toBeInTheDocument();
    expect(screen.queryByText("Mazda MX-5 2020 Green")).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
  });
});
