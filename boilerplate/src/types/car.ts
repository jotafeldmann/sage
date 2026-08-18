/** The shape of a car as served by the mock GraphQL API. */
export interface Car {
  id: string;
  make: string;
  model: string;
  year: number;
  color: string;
  /** Image URL for viewports up to 640px. */
  mobile: string;
  /** Image URL for viewports from 641px to 1023px. */
  tablet: string;
  /** Image URL for viewports from 1024px. */
  desktop: string;
}

/** Fields accepted when adding a car. The API assigns the id. */
export type CarInput = Omit<Car, "id">;
