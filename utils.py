import multiprocessing
from types import FunctionType

from joblib import Parallel, delayed


def parallelize(func: FunctionType, *list_args: list, n_jobs: int = -1) -> list:
    """Parallelize calls to a particular function.

    Parameters
    ----------
    func : FunctionType
        Function to be called.
    *list_args : list
        One list for each parameter in `func`. Each list should be the same
        length.
    n_jobs : int, default = -1
        Number of parallel jobs to run.

    Returns
    -------
    final_results : list
        List of values returned from calls to `func`.
    """

    def run_in_series(func, *list_args):
        results = []
        for args in zip(*list_args):
            results.append(func(*args))
        return results

    n_cpus = multiprocessing.cpu_count()
    if n_jobs <= 0:
        n_jobs += n_cpus
    n_jobs = min(n_jobs, n_cpus)

    results = Parallel(n_jobs=n_jobs)(
        delayed(run_in_series)(
            func,
            *[list_arg[i: i + n_jobs] for list_arg in list_args]
        )
        for i in range(0, len(list_args[0]), n_jobs)
    )

    final_results = []
    for sub_result in results:
        final_results.extend(sub_result)

    return final_results
