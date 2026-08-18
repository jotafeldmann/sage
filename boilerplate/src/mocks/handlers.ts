import { graphql, HttpResponse } from "msw";

import type { Car, CarInput } from "../types/car";
import { seedCars } from "./data";

/**
 * In-memory store backing the mock API. Reset between tests with
 * `resetCars()` so one test cannot leak state into the next.
 */
let cars: Car[] = [...seedCars];

export function resetCars(): void {
  cars = [...seedCars];
}

export function currentCars(): Car[] {
  return cars;
}

export const handlers = [
  graphql.query("GetCars", () => HttpResponse.json({ data: { cars } })),

  graphql.query<{ car: Car | null }, { id: string }>("GetCar", ({ variables }) =>
    HttpResponse.json({
      data: { car: cars.find((car) => car.id === variables.id) ?? null },
    }),
  ),

  graphql.mutation<{ addCar: Car }, { input: CarInput }>("AddCar", ({ variables }) => {
    const added: Car = { id: String(cars.length + 1), ...variables.input };
    cars = [...cars, added];
    return HttpResponse.json({ data: { addCar: added } });
  }),
];
