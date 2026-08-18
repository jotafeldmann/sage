import { gql } from "@apollo/client";

import type { Car, CarInput } from "../types/car";

export const GET_CARS = gql`
  query GetCars {
    cars {
      id
      make
      model
      year
      color
      mobile
      tablet
      desktop
    }
  }
`;

export const GET_CAR = gql`
  query GetCar($id: ID!) {
    car(id: $id) {
      id
      make
      model
      year
      color
      mobile
      tablet
      desktop
    }
  }
`;

export const ADD_CAR = gql`
  mutation AddCar($input: CarInput!) {
    addCar(input: $input) {
      id
      make
      model
      year
      color
      mobile
      tablet
      desktop
    }
  }
`;

export interface GetCarsData {
  cars: Car[];
}

export interface GetCarData {
  car: Car | null;
}

export interface GetCarVariables {
  id: string;
}

export interface AddCarData {
  addCar: Car;
}

export interface AddCarVariables {
  input: CarInput;
}
