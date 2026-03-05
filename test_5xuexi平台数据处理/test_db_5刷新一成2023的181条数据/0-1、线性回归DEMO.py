import numpy as np
import torch
import torch.nn as nn

class LinearRegressionModel(nn.Module):
    def __init__(self, input_size, output_size):
        super(LinearRegressionModel, self).__init__()
        self.linear = nn.Linear(input_size, output_size)

    def forward(self, x):
        out = self.linear(x)
        return out

input_dim = 1
output_dim = 1
model = LinearRegressionModel(input_dim, output_dim)
print(model)
device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model.to(device)

epochs = 1000
learning_rate = 0.01
optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)
criterion = nn.MSELoss()

x_values = [i for i in range(11)]
print(x_values)
x_train = np.array(x_values, dtype=np.float32)
x_train = x_train.reshape(-1, 1)
x_train.shape

y_values = [2 * i + 1 for i in x_values]
print(y_values)
y_train = np.array(y_values, dtype=np.float32)
y_train = y_train.reshape(-1, 1)
y_train.shape

for epoch in range(epochs):
    epoch += 1
    inputs = torch.from_numpy(x_train).to(device)
    labels = torch.from_numpy(y_train).to(device)
    outputs = model(inputs)
    loss = criterion(outputs, labels)

    # 梯度要清零每一次迭代
    optimizer.zero_grad()

    # 前向传播
    outputs = model(inputs)

    # 计算损失
    loss = criterion(outputs, labels)

    # 反向传播
    loss.backward()

    # 更新参数
    optimizer.step()

    if epoch % 50 == 0:
        print('epoch {}, loss {}'.format(epoch, loss.item()))

# 预测
predicted = model(torch.from_numpy(x_train).requires_grad_()).data.numpy()
print('predicted:', predicted)

# 保存模型
torch.save(model.state_dict(), 'model.pkl')
model.load_state_dict(torch.load('model.pkl'))

