import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Filters } from "../types";

const EMPTY: Filters = {
  locality: "all",
  suitability: "all",
  min_spi: "",
  max_payback: "",
  min_capacity: "",
  min_generation: "",
};

interface FilterContextValue {
  filters: Filters;
  emissionFactor: number;
  setFilter: (key: keyof Filters, value: string) => void;
  reset: () => void;
  setEmissionFactor: (value: number) => void;
  activeCount: number;
}

const Ctx = createContext<FilterContextValue | null>(null);

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<Filters>(EMPTY);
  const [emissionFactor, setEmissionFactor] = useState(0.71);

  const setFilter = useCallback((key: keyof Filters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const reset = useCallback(() => setFilters(EMPTY), []);

  const activeCount = useMemo(
    () =>
      Object.entries(filters).filter(
        ([, v]) => v !== "" && v !== "all",
      ).length,
    [filters],
  );

  const value = useMemo(
    () => ({
      filters,
      emissionFactor,
      setFilter,
      reset,
      setEmissionFactor,
      activeCount,
    }),
    [filters, emissionFactor, setFilter, reset, activeCount],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFilters(): FilterContextValue {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useFilters must be used inside FilterProvider");
  return ctx;
}
