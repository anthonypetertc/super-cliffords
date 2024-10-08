"""Module for defining the steps of a super-cliffor circuit."""

from abc import ABC, abstractmethod
from collections import Counter
import numpy as np
import stim
from supercliffords.gates import C3, ZH


class Step(ABC):
    """
    A step in a super-clifford circuit.
    params:
        N (int): The number of qubits in the circuit.
        when (str): Condition for when step should be applied.
    """

    def __init__(self, N, when):
        """
        Initialize the step.
        """
        self.N = N
        if when is None:
            when = "always"
        if isinstance(when, str) and when not in [
            "first",
            "always",
            "even",
            "odd",
        ]:
            raise ValueError(
                """Invalid value for 'when'. Currently accepted values are
                'first','always', 'even','odd'."""
            )

        self.when = when

    @abstractmethod
    def apply(self):
        pass

    def validate(self, step_count):
        when = self.when
        if when == "always" and step_count > 0:
            return True
        elif when == "first" and step_count == 0:
            return True
        elif when == "even" and step_count % 2 == 0 and step_count > 0:
            return True
        elif when == "odd" and step_count % 2 == 1 and step_count > 0:
            return True
        else:
            return False


class IdStep(Step):
    """
    Identity step.
    """

    def __init__(self, N):
        """
        Initialize the step.
        """
        super().__init__(N, when="first")

    def apply(self, s, step_count):
        """
        Apply the step.
        """
        if self.validate(step_count):
            c = stim.Circuit()
            c.append_operation("I", [self.N - 1])
            s.do(c)
        return s


class Initialize(Step):
    """
    Initialize the operator to an arbitrary product of X and Y.
    """

    def __init__(self, N, op_string=None):
        """
        Initialize the step.
        """
        super().__init__(N, when="first")
        self.op_string = self.prepare_op_string(op_string)

    def prepare_op_string(self, op_string):
        """
        Purpose: Prepare the operator string for the OTOC calculation.
        Inputs:
            - op_string (str or None) - a string of length N, containing only "X" and "Y" or None.
        Outputs:
            - op_string (str) - a string of length N, containing only "X" and "Y".
        """
        N = self.N
        if op_string is None:
            op_string = "X" * N
        if not isinstance(op_string, str):
            raise ValueError(
                "op_string must be a string, type is", type(op_string)
            )
        counter = Counter(op_string)
        assert set(counter.keys()) <= set(["X", "Y"])
        return op_string

    def apply(self, s, step_count):
        """
        Apply the step.
        """
        if self.validate(step_count):
            op_string = self.op_string
            counter = Counter(op_string)
            assert set(counter.keys()) <= set(["X", "Y"])
            N = len(op_string)
            c = stim.Circuit()
            c.append_operation("I", [N - 1])

            for i, letter in enumerate(op_string):
                if letter == "Y":
                    c.append_operation("X", [i])

            s.do(c)
        return s


class ThreeQuarterStep(Step):
    """
    Circuit that splits the qubits into 4 and applies C3 to 3/4 of the qubits
    being acted on, and T to the remaining qubits.
    """

    def __init__(self, N, slow):
        """
        Initialize the step.
        """
        super().__init__(N, when="always")
        self.slow = slow

    def apply(self, s, step_count):
        """
        Apply the step.
        """
        slow = self.slow
        if self.validate(step_count):
            r = [
                i for i in range(self.N)
            ]  # Randomly chooses which qubits to act on with the gates.
            np.random.shuffle(r)
            acted_on = self.N // slow
            quarter = acted_on // 4
            if quarter == 0:
                raise ValueError("Not enough qubits are being acted on!")

            for i in range(3 * quarter, acted_on):  # Apply ZH
                s.do(ZH(r[i]))

            s.do(C3(r[0], r[quarter], r[2 * quarter]))

            for i in range(1, quarter):  # Apply C3
                s.do(C3(r[i], r[quarter + i], r[2 * quarter + i]))

            c = stim.Circuit()
            c.append_operation("I", [self.N - 1])
            s.do(c)
        return s


class AlternatingEven(Step):
    """
    Circuit that acts with T on all qubits it acts on on even steps,
    and C3 on all qubits it acts on on odd steps.
    """

    def __init__(self, N, slow):
        """
        Initialize the step.
        """
        super().__init__(N, when="even")
        self.slow = slow

    def apply(self, s, step_count):
        """
        Apply the step.
        """
        slow = self.slow
        if self.validate(step_count):
            r = [
                i for i in range(self.N - 1)
            ]  # Randomly chooses which qubits to act on with the gates.
            np.random.shuffle(r)
            acted_on = self.N // slow
            for i in range(acted_on):
                s.do(ZH(r[i]))
        return s


class AlternatingOdd(Step):
    """
    Circuit that acts with T on all qubits it acts on on odd steps,
    and C3 on all qubits it acts on on even steps.
    """

    def __init__(self, N, slow):
        """
        Initialize the step.
        """
        super().__init__(N, when="odd")
        self.slow = slow

    def apply(self, s, step_count):
        """
        Apply the step.
        """
        slow = self.slow
        if self.validate(step_count):
            r = [
                i for i in range(self.N)
            ]  # Randomly chooses which qubits to act on with the gates.
            np.random.shuffle(r)
            acted_on = int(self.N / slow)
            third = acted_on // 3

            s.do(C3(r[0], r[third], r[2 * third]))
            for i in range(1, third):
                s.do(C3(r[i], r[third + i], r[2 * third + i]))
        return s


class StepSequence:
    """
    A sequence of steps in a super-clifford circuit.
    """

    def __init__(self, N, steps):
        """
        Initialize the sequence.
        """
        self.N = N
        self.steps = steps

    def apply(self, s, step_count):
        """
        Apply the sequence of steps.
        """
        for step in self.steps:
            s = step.apply(s, step_count)
        return s
