import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, timeout: 120000 });

export const api = {
  async algorithms() {
    const { data } = await client.get("/algorithms");
    return data;
  },
  async generate(count, seed, types) {
    const { data } = await client.post("/generate", { count, seed, types });
    return data.objects;
  },
  async nest(objects, settings, debug) {
    const { data } = await client.post("/nest", { objects, settings, debug });
    return data;
  },
  async benchmark(counts, settings, seed) {
    const { data } = await client.post("/benchmark", { counts, settings, seed });
    return data.results;
  },
};
