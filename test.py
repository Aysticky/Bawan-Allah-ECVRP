from docplex.mp.model import Model

mdl = Model("test")
x = mdl.binary_var(name="x")
mdl.maximize(x)
solution = mdl.solve()
print(solution)
