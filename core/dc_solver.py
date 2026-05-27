"""DC machine LSODA integrator.

Wraps scipy.integrate.odeint for step-by-step integration of DC ODEs.
Maintains history: t, x (state), y (outputs).
"""

from typing import Callable, List, Tuple
import numpy as np
from scipy.integrate import odeint

from core.dc_machine_model import DCMachineParams, DCMachineODEs


class DCSolver:
    """LSODA integrator for DC machine ODEs."""

    def __init__(
        self,
        config: str,
        params: DCMachineParams,
        t_eval: np.ndarray,
        x0: np.ndarray,
    ):
        """
        Parameters:
          config: 'sep_motor', 'shunt_motor', etc.
          params: DCMachineParams instance
          t_eval: Time vector for integration [t0, t1, ..., tf]
          x0: Initial state vector
        """
        self.config = config
        self.params = params
        self.odes = DCMachineODEs(config, params)
        self.t_eval = np.asarray(t_eval)
        self.x0 = np.asarray(x0)

        # Validate state dimension
        ode_func, n_states = self.odes.get_ode_func()
        if len(self.x0) != n_states:
            raise ValueError(
                f"x0 has {len(self.x0)} states; config '{config}' expects {n_states}"
            )

        self.ode_func = ode_func
        self.n_states = n_states

        # Storage for results
        self.t = None
        self.x = None
        self.y = None

    def run(self, Va_func: Callable[[float], float]) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        Integrate and store results.

        Parameters:
          Va_func: Function Va(t) returning armature voltage at time t.

        Returns:
          (t, x, y_dict) where:
            t: time vector (same as t_eval)
            x: state array, shape (n_steps, n_states)
            y_dict: dict with keys ['ia', 'ifd', 'wm', 'Te', 'Ea'], each shape (n_steps,)
        """

        def ode_wrapper(x, t):
            """scipy.integrate.odeint expects f(x, t); we wrap to apply Va(t)."""
            Va = Va_func(t)
            return self.ode_func(t, x, Va)

        # Integrate
        self.x = odeint(ode_wrapper, self.x0, self.t_eval, full_output=False)
        self.t = self.t_eval

        # Compute outputs at each step
        self.y = self._compute_outputs_all()

        return self.t, self.x, self.y

    def _compute_outputs_all(self) -> dict:
        """Compute outputs at all time steps."""
        n_steps = len(self.t)
        outputs = {
            "ia": np.zeros(n_steps),
            "ifd": np.zeros(n_steps),
            "wm": np.zeros(n_steps),
            "Te": np.zeros(n_steps),
            "Ea": np.zeros(n_steps),
        }

        for i in range(n_steps):
            y_dict = DCMachineODEs.compute_outputs(self.config, self.x[i], self.params)
            for key in outputs:
                if key in y_dict:
                    outputs[key][i] = y_dict[key]

        return outputs

    def get_results(self) -> Tuple[np.ndarray, np.ndarray, dict]:
        """Return (t, x, y) after run()."""
        if self.x is None:
            raise RuntimeError("Must call run() first")
        return self.t, self.x, self.y

    def get_final_state(self) -> dict:
        """Return final values of key variables."""
        if self.y is None:
            raise RuntimeError("Must call run() first")

        return {
            "ia": self.y["ia"][-1],
            "ifd": self.y["ifd"][-1],
            "wm": self.y["wm"][-1],
            "Te": self.y["Te"][-1],
            "Ea": self.y["Ea"][-1],
            "t_final": self.t[-1],
        }
