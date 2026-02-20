"""
Strategy Optimizer for Quantitative Analysis.

Provides parameter optimization capabilities.
"""

import asyncio
import itertools
import logging
import random
from datetime import datetime
from typing import Any, Callable

import numpy as np

from openfinance.models.quant import (
    Strategy,
    OptimizationConfig,
    OptimizationResult,
    OptimizeMethod,
    BacktestConfig,
    BacktestResult,
)

logger = logging.getLogger(__name__)


class StrategyOptimizer:
    """Optimizer for strategy parameters.

    Provides:
    - Grid search optimization
    - Random search optimization
    - Genetic algorithm optimization
    - Bayesian optimization (placeholder)
    """

    def __init__(self, backtest_func: Callable | None = None) -> None:
        self._backtest_func = backtest_func

    def set_backtest_function(self, func: Callable) -> None:
        """Set the backtest function for optimization."""
        self._backtest_func = func

    async def optimize(
        self,
        strategy: Strategy,
        config: OptimizationConfig,
        backtest_config: BacktestConfig,
    ) -> OptimizationResult:
        """Run parameter optimization.

        Args:
            strategy: Strategy to optimize.
            config: Optimization configuration.
            backtest_config: Backtest configuration.

        Returns:
            OptimizationResult with best parameters.
        """
        if not self._backtest_func:
            raise ValueError("Backtest function not set")

        if config.method == OptimizeMethod.GRID_SEARCH:
            return await self._grid_search(strategy, config, backtest_config)
        elif config.method == OptimizeMethod.RANDOM_SEARCH:
            return await self._random_search(strategy, config, backtest_config)
        elif config.method == OptimizeMethod.GENETIC:
            return await self._genetic_optimization(strategy, config, backtest_config)
        else:
            return await self._random_search(strategy, config, backtest_config)

    async def _grid_search(
        self,
        strategy: Strategy,
        config: OptimizationConfig,
        backtest_config: BacktestConfig,
    ) -> OptimizationResult:
        """Grid search optimization."""
        param_ranges = self._build_param_ranges(config.parameters)
        all_combinations = list(itertools.product(*param_ranges.values()))
        param_names = list(param_ranges.keys())

        if len(all_combinations) > config.max_iterations:
            all_combinations = all_combinations[:config.max_iterations]

        results = []
        best_score = float("-inf")
        best_params = {}

        for i, combo in enumerate(all_combinations):
            params = dict(zip(param_names, combo))

            test_strategy = strategy.model_copy()
            test_strategy.parameters.update(params)

            try:
                backtest_result = await self._run_backtest(
                    test_strategy,
                    backtest_config,
                )
                score = self._get_objective_score(backtest_result, config.objective)

                results.append({
                    "params": params,
                    "score": score,
                    "metrics": backtest_result.metrics.model_dump() if backtest_result.metrics else {},
                })

                if score > best_score:
                    best_score = score
                    best_params = params

            except Exception as e:
                logger.warning(f"Backtest failed for params {params}: {e}")

            if i % 10 == 0:
                logger.info(f"Grid search progress: {i}/{len(all_combinations)}")

        return OptimizationResult(
            strategy_id=strategy.strategy_id,
            method=OptimizeMethod.GRID_SEARCH,
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            duration_ms=0,
        )

    async def _random_search(
        self,
        strategy: Strategy,
        config: OptimizationConfig,
        backtest_config: BacktestConfig,
    ) -> OptimizationResult:
        """Random search optimization."""
        if config.seed:
            random.seed(config.seed)
            np.random.seed(config.seed)

        results = []
        best_score = float("-inf")
        best_params = {}

        for i in range(config.max_iterations):
            params = self._sample_params(config.parameters)

            test_strategy = strategy.model_copy()
            test_strategy.parameters.update(params)

            try:
                backtest_result = await self._run_backtest(
                    test_strategy,
                    backtest_config,
                )
                score = self._get_objective_score(backtest_result, config.objective)

                results.append({
                    "params": params,
                    "score": score,
                    "metrics": backtest_result.metrics.model_dump() if backtest_result.metrics else {},
                })

                if score > best_score:
                    best_score = score
                    best_params = params

            except Exception as e:
                logger.warning(f"Backtest failed for params {params}: {e}")

        return OptimizationResult(
            strategy_id=strategy.strategy_id,
            method=OptimizeMethod.RANDOM_SEARCH,
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            duration_ms=0,
        )

    async def _genetic_optimization(
        self,
        strategy: Strategy,
        config: OptimizationConfig,
        backtest_config: BacktestConfig,
    ) -> OptimizationResult:
        """Genetic algorithm optimization."""
        if config.seed:
            random.seed(config.seed)
            np.random.seed(config.seed)

        population_size = min(50, config.max_iterations // 2)
        generations = config.max_iterations // population_size
        mutation_rate = 0.1
        elite_ratio = 0.2

        population = [
            self._sample_params(config.parameters)
            for _ in range(population_size)
        ]

        results = []
        best_score = float("-inf")
        best_params = {}

        for gen in range(generations):
            fitness_scores = []

            for individual in population:
                test_strategy = strategy.model_copy()
                test_strategy.parameters.update(individual)

                try:
                    backtest_result = await self._run_backtest(
                        test_strategy,
                        backtest_config,
                    )
                    score = self._get_objective_score(backtest_result, config.objective)
                    fitness_scores.append((individual, score))

                    results.append({
                        "params": individual,
                        "score": score,
                        "generation": gen,
                    })

                    if score > best_score:
                        best_score = score
                        best_params = individual

                except Exception as e:
                    fitness_scores.append((individual, float("-inf")))

            fitness_scores.sort(key=lambda x: x[1], reverse=True)

            elite_count = int(population_size * elite_ratio)
            new_population = [ind for ind, _ in fitness_scores[:elite_count]]

            while len(new_population) < population_size:
                parent1 = self._tournament_select(fitness_scores)
                parent2 = self._tournament_select(fitness_scores)
                child = self._crossover(parent1, parent2, config.parameters)
                child = self._mutate(child, config.parameters, mutation_rate)
                new_population.append(child)

            population = new_population

            logger.info(f"Generation {gen}: best_score={best_score:.4f}")

        return OptimizationResult(
            strategy_id=strategy.strategy_id,
            method=OptimizeMethod.GENETIC,
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            duration_ms=0,
        )

    async def _run_backtest(
        self,
        strategy: Strategy,
        config: BacktestConfig,
    ) -> BacktestResult:
        """Run backtest for a strategy."""
        if self._backtest_func:
            return await self._backtest_func(strategy, config)

        return BacktestResult(
            backtest_id="mock",
            strategy_id=strategy.strategy_id,
            config=config,
            duration_ms=0,
            start_date=config.start_date,
            end_date=config.end_date,
        )

    def _get_objective_score(
        self,
        result: BacktestResult,
        objective: str,
    ) -> float:
        """Extract objective score from backtest result."""
        if not result.metrics:
            return float("-inf")

        objective_map = {
            "sharpe_ratio": result.metrics.sharpe_ratio,
            "annual_return": result.metrics.annual_return,
            "total_return": result.metrics.total_return,
            "sortino_ratio": result.metrics.sortino_ratio,
            "calmar_ratio": result.metrics.calmar_ratio,
            "max_drawdown": -result.metrics.max_drawdown,
        }

        return objective_map.get(objective, result.metrics.sharpe_ratio)

    def _build_param_ranges(
        self,
        params: dict[str, dict[str, Any]],
    ) -> dict[str, list[Any]]:
        """Build parameter ranges for grid search."""
        ranges = {}
        for name, config in params.items():
            if "values" in config:
                ranges[name] = config["values"]
            elif "min" in config and "max" in config and "step" in config:
                step = config["step"]
                values = []
                v = config["min"]
                while v <= config["max"]:
                    values.append(v)
                    v += step
                ranges[name] = values
            elif "min" in config and "max" in config:
                ranges[name] = [config["min"], config["max"]]
            else:
                ranges[name] = [config.get("default", 0)]

        return ranges

    def _sample_params(
        self,
        params: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Sample random parameters."""
        sampled = {}
        for name, config in params.items():
            if "values" in config:
                sampled[name] = random.choice(config["values"])
            elif "min" in config and "max" in config:
                if config.get("type") == "int":
                    sampled[name] = random.randint(config["min"], config["max"])
                else:
                    sampled[name] = random.uniform(config["min"], config["max"])
            else:
                sampled[name] = config.get("default")

        return sampled

    def _tournament_select(
        self,
        fitness_scores: list[tuple[dict, float]],
        tournament_size: int = 3,
    ) -> dict[str, Any]:
        """Tournament selection for genetic algorithm."""
        tournament = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
        winner = max(tournament, key=lambda x: x[1])
        return winner[0]

    def _crossover(
        self,
        parent1: dict[str, Any],
        parent2: dict[str, Any],
        param_config: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Crossover operation for genetic algorithm."""
        child = {}
        for key in parent1.keys():
            if random.random() < 0.5:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        return child

    def _mutate(
        self,
        individual: dict[str, Any],
        param_config: dict[str, dict[str, Any]],
        mutation_rate: float,
    ) -> dict[str, Any]:
        """Mutation operation for genetic algorithm."""
        mutated = individual.copy()
        for key, value in mutated.items():
            if random.random() < mutation_rate:
                config = param_config.get(key, {})
                if "values" in config:
                    mutated[key] = random.choice(config["values"])
                elif "min" in config and "max" in config:
                    if config.get("type") == "int":
                        mutated[key] = random.randint(config["min"], config["max"])
                    else:
                        mutated[key] = random.uniform(config["min"], config["max"])
        return mutated
