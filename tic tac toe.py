import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # 设置后端，避免属性错误
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class Agent():
    def __init__(self, XXOO_Index, Epsilon, Alpha):
        self.index = XXOO_Index
        self.epsilon = Epsilon
        self.alpha = Alpha
        self.value = np.ones((3,3,3,3,3,3,3,3,3)) * 0.5
        self.stored_outcome = np.zeros(9).astype(np.int8)
    def reset(self):
        self.stored_outcome = np.zeros(9).astype(np.int8)
    def act(self, state):
        outcome = state.copy()
        available = np.where(outcome == 0)[0]
        if np.random.binomial(1,self.epsilon) == 1:
            outcome[np.random.choice(available)] = self.index
        else:
            temp_value = np.zeros(len(available))
            for i in range(len(available)):
                temp_outcome = outcome.copy()
                temp_outcome[available[i]] = self.index
                temp_value[i] = self.value[tuple(temp_outcome)]
            choice = np.argmax(temp_value)
            outcome[available[choice]] = self.index
        error = self.value[tuple(outcome)] - self.value[tuple(self.stored_outcome)]
        self.value[tuple(self.stored_outcome)] += self.alpha * error
        self.stored_outcome = outcome.copy()
        return outcome

def judge(outcome, XXOO_Index):
    winner = 0
    if 0 not in outcome:
        winner = 3
        print("No winner")
        print(outcome[0:3])
        print(outcome[3:6])
        print(outcome[6:9])
    if (outcome[0:3] == XXOO_Index).all() or (outcome[3:6] == XXOO_Index).all() or (outcome[6:9] == XXOO_Index).all():
        winner = XXOO_Index
    if (outcome[0:7:3] == XXOO_Index).all() or (outcome[1:8:3] == XXOO_Index).all() or (outcome[2:9:3] == XXOO_Index).all():
        winner = XXOO_Index
    if (outcome[0:9:4] == XXOO_Index).all() or (outcome[2:7:2] == XXOO_Index).all():
        winner = XXOO_Index
    return winner

Agent1 = Agent(1, 0.1, 0.01)
Agent2 = Agent(2, 0.1, 0.01)
Trile = 10000
Winner = np.zeros(Trile)
for i in range(Trile):
    if i == 4000:
        Agent1.epsilon = 0
        Agent2.epsilon = 0
    Agent1.reset()
    Agent2.reset()
    winner = 0
    State = np.zeros(9).astype(np.int8)
    while winner == 0:
        Outcome = Agent1.act(State)
        winner = judge(Outcome, 1)
        if winner == 1:
            print(i, ':Player 1 wins!')
            print(Outcome[0:3])
            print(Outcome[3:6])
            print(Outcome[6:9])
            Agent1.value[tuple(Outcome)] = 1
            Agent2.value[tuple(State)] = -1
        elif winner == 0:
            State = Agent2.act(Outcome)
            winner = judge(State, 2)
            if winner == 2:
                print(i, ':Player 2 wins!')
                print(State[0:3])
                print(State[3:6])
                print(State[6:9])
                Agent1.value[tuple(Outcome)] = -1
                Agent2.value[tuple(State)] = 1
    Winner[i] = winner

cumulative = np.zeros((10000, 3))
for i in range(3):
    cumulative[:, i] = np.cumsum(Winner == i+1) / np.arange(1, 10001)

# 打印统计信息
print("="*50)
print("最终统计结果：")
print(f"总游戏局数: {len(Winner)}")
print(f"玩家1获胜: {np.sum(Winner == 1)} 局 ({np.sum(Winner == 1)/len(Winner)*100:.2f}%)")
print(f"玩家2获胜: {np.sum(Winner == 2)} 局 ({np.sum(Winner == 2)/len(Winner)*100:.2f}%)")
print(f"平局: {np.sum(Winner == 3)} 局 ({np.sum(Winner == 3)/len(Winner)*100:.2f}%)")

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# 分别绘制三种情况的概率密度
results = ['玩家1胜', '玩家2胜', '平局']
colors = ['blue', 'red', 'green']
data = [Winner == 1, Winner == 2, Winner == 3]

for i, (result, color, mask) in enumerate(zip(results, colors, data)):
    # 计算滑动窗口概率密度
    window = 100  # 窗口大小
    density = np.zeros(len(Winner) - window + 1)

    for j in range(len(density)):
        density[j] = np.mean(mask[j:j + 200])

    axes[i].plot(density, color=color, linewidth=1)
    axes[i].set_xlabel('游戏次数')
    axes[i].set_ylabel('概率密度')
    axes[i].set_title(f'{result}的概率密度分布')
    axes[i].grid(True, alpha=0.3)
    # axes[i].set_ylim(0, 1)  # 固定y轴范围便于比较

plt.tight_layout()
plt.show()