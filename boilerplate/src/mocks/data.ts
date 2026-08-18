import type { Car } from "../types/car";

/** Placeholder image service, so the mock needs no bundled binaries. */
function image(seed: string, width: number, height: number): string {
  return `https://picsum.photos/seed/${seed}/${width}/${height}`;
}

export const seedCars: Car[] = [
  {
    id: "1",
    make: "Toyota",
    model: "Corolla",
    year: 2021,
    color: "Silver",
    mobile: image("corolla", 320, 200),
    tablet: image("corolla", 640, 400),
    desktop: image("corolla", 1024, 640),
  },
  {
    id: "2",
    make: "Honda",
    model: "Civic",
    year: 2019,
    color: "Blue",
    mobile: image("civic", 320, 200),
    tablet: image("civic", 640, 400),
    desktop: image("civic", 1024, 640),
  },
  {
    id: "3",
    make: "Ford",
    model: "Mustang",
    year: 2023,
    color: "Red",
    mobile: image("mustang", 320, 200),
    tablet: image("mustang", 640, 400),
    desktop: image("mustang", 1024, 640),
  },
  {
    id: "4",
    make: "Volkswagen",
    model: "Golf",
    year: 2018,
    color: "White",
    mobile: image("golf", 320, 200),
    tablet: image("golf", 640, 400),
    desktop: image("golf", 1024, 640),
  },
  {
    id: "5",
    make: "Tesla",
    model: "Model 3",
    year: 2022,
    color: "Black",
    mobile: image("model3", 320, 200),
    tablet: image("model3", 640, 400),
    desktop: image("model3", 1024, 640),
  },
];
