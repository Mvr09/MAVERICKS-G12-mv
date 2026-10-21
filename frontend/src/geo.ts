// Approximate coordinates (city centre) of the supplier cities in the challenge
// catalogue, for the exposure map. Key: "City|Country" exactly as in the Excel.
// Only used to draw points; no geocoding service is called.
export const CITY_COORDS: Record<string, [number, number]> = {
  "Ahmedabad|India": [72.58, 23.03],
  "Antwerp|Belgium": [4.4, 51.22],
  "Barcelona|Spain": [2.17, 41.39],
  "Basel|Switzerland": [7.59, 47.56],
  "Bengaluru|India": [77.59, 12.97],
  "Bergamo|Italy": [9.67, 45.7],
  "Boston|USA": [-71.06, 42.36],
  "Cologne|Germany": [6.96, 50.94],
  "Cork|Ireland": [-8.47, 51.9],
  "Darmstadt|Germany": [8.65, 49.87],
  "Dublin|Ireland": [-6.26, 53.35],
  "Hangzhou|China": [120.16, 30.27],
  "Ho Chi Minh City|Vietnam": [106.63, 10.82],
  "Hsinchu|Taiwan": [120.97, 24.8],
  "Hyderabad|India": [78.49, 17.39],
  "Kaohsiung|Taiwan": [120.3, 22.63],
  "Lancaster|USA": [-76.31, 40.04],
  "Lodz|Poland": [19.46, 51.76],
  "Ludwigshafen|Germany": [8.44, 49.48],
  "Madrid|Spain": [-3.7, 40.42],
  "Mainz|Germany": [8.27, 50.0],
  "Milan|Italy": [9.19, 45.46],
  "Monterrey|Mexico": [-100.32, 25.69],
  "Osaka|Japan": [135.5, 34.69],
  "Oslo|Norway": [10.75, 59.91],
  "Rotterdam|Netherlands": [4.48, 51.92],
  "San Juan|Puerto Rico (USA)": [-66.11, 18.47],
  "Sao Paulo|Brazil": [-46.63, -23.55],
  "Shanghai|China": [121.47, 31.23],
  "Singapore|Singapore": [103.82, 1.35],
  "Taizhou|China": [121.42, 28.66],
  "Tangier|Morocco": [-5.83, 35.76],
  "Vadodara|India": [73.18, 22.31],
  "Valencia|Spain": [-0.38, 39.47],
  "Wuhan|China": [114.31, 30.59],
  "Xi'an|China": [108.94, 34.34],
  "Zurich|Switzerland": [8.54, 47.38],
};

export function coordsOf(
  city: string | null,
  country: string | null,
): [number, number] | null {
  return city && country ? (CITY_COORDS[`${city}|${country}`] ?? null) : null;
}
