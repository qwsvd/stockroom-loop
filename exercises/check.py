"""Run explicitly with Python and an exercise number."""
import sys
from my_agent import take, loop, verify


def first():
    assert take(2,1) == (1,True)
    for qty in (3, True, -1, 0):
        assert take(2,qty) == (2,False)


def second():
    def policy(history):
        return "take" if history and history[-1][1] == {"stock":1} else "inspect"
    def apply(action):
        return {"stock":1} if action=="inspect" else {"terminal":"done"}
    assert loop(policy,apply,4) == [("inspect",{"stock":1}),("take",{"terminal":"done"})]
    assert len(loop(lambda h:"inspect",apply,3)) == 3


def third():
    assert verify((2,2),(0,2),(2,0),2)
    assert not verify((2,2),(2,0),(0,2),2)
    assert not verify((2,2),(1,2),(2,0),2)
    assert not verify((2,2),(1,2),(1,0),2)


if __name__ == "__main__":
    {"1":first,"2":second,"3":third}[sys.argv[1]]()
    print("Examples passed.")
