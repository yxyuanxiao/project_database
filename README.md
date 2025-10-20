# 图像质量标注系统

## 环境配置

### 配置Python环境

```bash
git clone https://github.com/yxyuanxiao/project_database.git
cd project_database
conda create -n annotation python=3.10
conda activate annotation
pip install -r requirements.txt
```

### 配置Mongodb

#### 下载

```bash
# 以Ubuntu 20.04 x64为例子，其他版本在https://www.mongodb.com/try/download/community-edition/releases/archive中下载
wget https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-ubuntu2004-4.4.29.tgz
tar -zxvf mongodb-linux-x86_64-ubuntu1604-4.2.8.tgz
mv mongodb-linux-x86_64-ubuntu1604-4.2.8  /usr/local/mongodb4  # 将解压包拷贝到指定目录
# MongoDB 的可执行文件位于 bin 目录下，所以可以将其添加.bashrc的 PATH 路径中：
export PATH=<mongodb-install-directory>/bin:$PATH
# <mongodb-install-directory> 为你 MongoDB 的安装路径。如本文的 /usr/local/mongodb4 。
# export PATH=/usr/local/mongodb4/bin:$PATH
```

#### 创建数据库目录

```bash
sudo mkdir -p /usr/local/mongodb4/data
sudo mkdir -p /usr/local/mongodb4/log
sudo chown `whoami` /usr/local/mongodb4/data  # 设置权限
sudo chown `whoami` /usr/local/mongodb4/log     # 设置权限
```

#### 启动 Mongodb 服务

```bash
mongod --dbpath /usr/local/mongodb4/data --logpath /usr/local/mongodb4/log --fork
# 未设置环境变量则使用下面这条
# /usr/local/mongodb4/bin/mongod --dbpath /usr/local/mongodb4/data --logpath /usr/local/mongodb4/log --fork
```

### 导入数据

数据目录格式为，可以参考文件夹`Set5`

```
.
├── lq_image
│   ├── 1.png
│   ├── 2.png
│   ...
│
├── method_1
│   ├── 1.png #和lq_image中文件重名
│   ├── 2.png 
│   ...
│
├── method_2
│   ├── 1.png #和lq_image中文件重名
│   ├── 2.png 
│   ...
...
├── methods.json
├── files.json
```

其中，`methods.json`文件格式为

```json
{
    "lq_path": "文件夹lq_image的绝对路径", 
    "methods": [
        {
            "name": "method_1",
            "path": "文件夹method_1的绝对路径"
        },
        {
            "name": "method_2",
            "path": "文件夹method_2的绝对路径"
        },
    ]
}
```

`files.json`文件格式为

```json
[
    {
        "image": "文件夹lq_image的第一张图片的文件名(包括后缀名)",
        "scene": "标签(任意)",
    },
    {
        "image": "文件夹lq_image的第二张图片的文件名(包括后缀名)",
        "scene": "标签(任意)",
    }
]
```

设置完`json`后，导入数据到数据库

```
python -m utils.import --json_config_path methods.json --files_json_path files.json
```

### 运行代码

```bash
python main.py # 进入用户界面
python main.py --role admin # 进入管理员界面
```

---

## 项目介绍

主要是为不同修复模型修复图像进行打分

### 登陆界面

- 注册，检查是否重复用户名
- 登陆，使用用户名登陆

### 标注界面

- 上一张、下一张，记录每个用户标注的历史，可以通过上一张下一张查看自己标注历史，并进行修改
- 如果用户在点击下一张时，历史记录中无下一张，则会自动获得新的标注任务
- 每个用户在标注时都设计了互斥锁，防止重复标记同一条数据。如果用户5分钟内未完成标注，互斥锁会过期，系统会自动清理过期的锁
- 可以进行打分，使用llm生成评价，保存标注结果
- 可以查看标注统计

### 标注结果展示

- 用户可以在这里看到自己所有已经标注过的记录，并且进行修改
- 管理员可以在这里看到所有人已经标注过的记录、未标注的数据和正在标注的数据，并且进行修改
- 可以根据任务ID跳转到指定任务

