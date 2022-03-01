# 钢琴社服务器维护指南

Credit to 胡大
Tutorial by boshi

## 简介

钢琴社微信公众号后台基于Nginx+Python+Flask。

后台本体由单个文件夹组成：

- klavx/
  - whls/
    - requirements.txt
  - log/
    - flask.log
  - conf.ini
  - courses.txt
  - db
  - default.ini
  - deploy.sh
  - main.py
  - music.db
  - music.py
  - patterns.py
  - performers.txt
  - processor.py
  - syncdb.sh
  - utils.py

要想让其成功运行，还需要在其所在的服务器正确配置nginx、python，还需要在微信控制台设置正确的服务器地址。

如果你是计算机大佬，这个文档可以帮你快速了解后台的运作模式，并在配置时帮助你少走许多弯路，另外还能帮助你为其开发一些新的功能。如果你是计算机小白，完全按照这个文档操作可以大概率保证公众号后台的正常运行和成功迁移。

## 基本信息

如果下述信息在你接手维护钢琴社服务器的时候发生了改变，请修改本文档，以方便后人使用

在换届交接过程中，请将本文档交予下一任技术部负责人

**目前使用的服务器正在与提琴社合租，提琴社方面也拥有一个root权限的账号**

**如果社团的服务器到期，续租的费用由社团承担，请联系当届的团支书进行报销**

**目前使用的服务在2022年8月到期前使用`20级安博施`的学生认证购买，如要续租请在学生认证界面续租，!!不要!!在控制台界面续租！！！**

**密码不要外泄！！！**

| 项目名称       | 项目内容                           |
| -------------- | ---------------------------------- |
| 服务器供应商   | 腾讯云                             |
| 服务器配置     | 1core+2G+50G+1Mbps                 |
| 服务器操作系统 | ubuntu server 18.04                |
| 服务器公网ip   | ??.??.??.??                      |
| 服务器到期时间 | 2022-08-30 12:16:21                |
| 服务器登陆账号 | ubuntu                             |
| 服务器登陆密码 | ??????                     |
| 腾讯云注册邮箱 | pkupiano_public@126.com            |
| 腾讯云密码     | ??????（邮箱密码也是这个） |

## 和服务器互相认识

### 认识服务器

**如果你已经使用过腾讯云或阿里云或某提供商的虚拟云服务器（VPS），可以跳过本部分**

用腾讯云注册邮箱登陆腾讯云后可以进入控制台查看服务器的底层信息，在这里可以做的事包括但不限于：

- 开关机
- 续费（不要在这里续费！！！在这里续费没有学生优惠）
- 升降配
- 查看公网ip
- 监控系统负载

### 让服务器认识你

#### 密码

通过服务器的密码，可以用 `ssh` 命令登陆服务器

在 `ubuntu` 下输入以下命令并在后续提示中输入密码即可登陆

```bash
ssh ubuntu@82.157.114.38
```

#### rsa密钥

使用rsa密钥可以在使用上述命令时免去输入密码的麻烦

该方法的原理是根据你计算机独有的信息生成一个独有的密钥对，将私钥保存在本地的某个指定文件夹内，再将公钥追加到服务器上某个指定文件末尾，在ssh连接服务器时系统将会自动判断本地的私钥是否与服务器上的某个公钥匹配，弱匹配则不需要输入密码。

- 如果你是windows用户：
  - 在命令行输入

  - ```bash
    ssh-keygen -t rsa
    ```

  - 然后一路回车跳过所有多余的信息

  - 你将会在某个文件夹看到该命令生成的公钥`id_rsa.pub`和私钥`id_rsa`

  - 将私钥和公钥同时保存在`C:\Users\你的用户名\.ssh`下

  - 然后将公钥上传至服务器

  - ```bash
    cat id_rsa.pub | ssh 服务器用户@服务器IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
    ```

- 如果你是linux用户

  - 在命令行输入

  - ```bash
    ssh-keygen -t rsa
    ```

  - 然后一路回车跳过所有多余的信息

  - 你将会在 `~/.ssh` 下看到公钥`id_rsa.pub`和私钥`id_rsa`

  - 然后将公钥上传至服务器

  - ```bash
    cat ~/.ssh/id_rsa.pub | ssh 服务器用户@服务器IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
    ```

#### 添加新用户

连接到服务器后在终端输入

```bash
sudo adduser 新用户名
```

即可新建用户

再在 `sudo vim /etc/sudoers` 末尾追加：

```bash
新用户名 ALL=(ALL) ALL
```

即可给新用户添加root权限

## 新服务器环境配置

如果你获得了一个**新的ubuntu服务器**，并希望将微信后台迁移到新服务器，可以参考这部分内容。

当然似乎该服务也可以通过uwsgi运行，稳定性更高，在之前的服务器上是这么运行的，然而笔者技术水平过低，只能用比较笨的方法让服务运行起来

1. 首先我们需要在新服务器安装nginx：

   ```bash
   sudo apt install nginx
   service nginx start  # 启动nginx
   service nginx reload  # 重新加载nginx配置文件
   ```

2. 然后nginx就安装好了，下一步是将旧的公众号后台迁移（全部拷贝）过来：

   在新的服务器段修改权限以使得可以接受传来的文件：

   ```bash
   sudo chmod 777 /var/www 
   ```

   在旧的服务器终端输入：

   ```bash
   scp -r /var/www/klavx/ ubuntu@新服务器地址:/var/www/klavx/
   ```

   于是整个公众号后台都被迁移过来了。

3. 发挥你的聪明才智，安装Python3.6（一般的服务器会自带）以及venv模块

   ```bash
   sudo apt install python3-venv
   ```

4. 删除原有的python虚拟环境

   ```bash
   sudo rm -r /var/www/klavx/venv
   ```

5. 创建新的python虚拟环境

   ```bash
   cd /var/www/klavx
   python3 -m venv venv
   ```

6. 激活新的python虚拟环境

   ```bash
   source venv/bin/activate
   ```

7. 安装依赖库

   对于不同版本的ubuntu server可能需要安装不同的依赖，若按照下面的方法搞不定的话可以用pip手动安装一些库

   ```bash
   pip install -r ./whls/requirements.txt
   ```

8. 配置nginx

   修改nginx的配置文件`/etc/nginx/sites-avilable/default`：

   ```bash
   sudo nano /etc/nginx/sites-avilable/default
   ```

   并在原有的

   ```bash
   	location / {
   		# First attempt to serve request as file, then
   		# as directory, then fall back to displaying a 404.
   		try_files $uri $uri/ =404;
   	}
   ```

   后面追加：

   ```bash
   	# klavx
   	location = /klavx {rewrite ^ /klavx/;}
   	location /klavx/ {
   		include uwsgi_params;
   		proxy_pass http://127.0.0.1:5000/klavx/;
   	}
   ```

9. 至此为止，服务器上的配置工作基本完工，先尝试**在虚拟环境内**运行后台：

   确保自己在`venv`的虚拟环境内（执行`source venv/bin/activate`进入虚拟环境，`deactivate`退出）

   ```bash
   cd /var/www/klavx/
   python main.py runserver
   ```

   如果可以成功运行（有红色的警告也不管他（真的不用管）），那么恭喜你可以继续了

   如果不能成功运行，请自行解决或联系上一届技术部成员寻求帮助

10. 接下来尝试修改微信设置，将公众号消息转发给服务器

    进入公众号管理平台 https://mp.weixin.qq.com/

    将“设置与开发”栏目的“基本配置”中的“服务器配置(已启用)”下的“服务器地址”改成`http://新服务器地址/klavx/`

    如果成功修改，那么恭喜你，公众号后台上线了，快去发消息调戏

    如果不能成功修改，请自行解决或联系上一届技术部成员寻求帮助

11. 接下来只需要将运行程序的命令打包成一个服务开机自启后台运行即可（后台运行）

    ```bash
    cd /etc/init.d/
    sudo touch klavx.sh
    sudo nano klavx.sh
    ```

    然后在打开的文件`klavx.sh`内写入：

    ```bash
    cd /var/www/klavx
    source /var/www/klavx/venv/bin/activate
    uwsgi --daemonize2 --ini /var/www/klavx/new.ini
    ```

    然后将该脚本赋予可执行权限并设置为开机启动：

     ```bash
     sudo chmod 777 klavx.sh
     sudo update-rc.d klavx.sh defaults 90
     ```

    要是发现程序没有在运行想要手动运行，只需要找到这个`.sh`文件并执行这个文件即可 
    
    如果程序正在运行，你想要停止它：
    
    ```bash
    killall -s INT uwsgi
    ```
    

## 服务器维护

### 服务挂了！

- 也许是服务器挂了

  检查以下服务器有没有在运行

- 也许是服务没有在运行

  这时好办，手动运行上面提到的`klavx.sh`即可

- 也许是服务崩溃了

  所以要把他杀死

  ```bash
  killall -s INT uwsgi
  ```
  
  然后重启（手动运行`klavx.sh`）
  
- 也许是系统崩溃了

  可以重启整个服务器

  **请务必联系所有可能在使用服务器的人，经过同意再重启**，因为由于该服务器是公用服务器，可能有其他服务在该服务器上运行，目前有提琴社同学在使用

  重启的代价较大，请三思而后行

### 服务没挂！就是想瞅瞅

- 可以去瞅瞅 `/var/www/klavx/log/klavx.log`里面记录了所有人调戏公众号的记录以及预约琴房等记录，但是读起来很不方便
- 还可以去瞅瞅腾讯云控制台的监控界面，系统负载一目了然

### 修改选课名单

1. 切换路径到`/var/www/klavx`下

   *经过上面的教学你一定已经学会了！请发挥你的聪明才智！*

2. 修改当前目录下的 `main.py` 的 `refreshCourses` 函数，将其中的 `startDate` 和 `endDate` 变量修改为本学期钢琴课的起止日期

   *不会的话问问身边会Python的大佬*

3. 将 `/var/www/klavx` 下的 `course.txt` 修改为新的选课名单

4. 进入虚拟环境

   *经过上面的教学你一定已经学会了！请发挥你的聪明才智！*

5. 刷新

   ```bash
   sudo python3 main.py refreshcourses
   ```

   该操作会显示：”Old courses will be deleted, are you sure? ” 

   输入”Yes”后即刷新选课名单，（当然也可以输入yes,Y,y）

### 给演奏部成员赋权

1. 首先搞到一张新的演奏部成员的名单

2. 将名字一行一个输入到一个`xxx.txt`文件中

3. 将`xxx.txt`上传到服务器的`/var/www/klavx/`目录下

   ```bash
   scp ./xxx.txt ubuntu@服务器IP:/var/www/klavx/
   ```

4. 到服务器上的`/var/www/klavx/`目录下运行（确保在虚拟环境内）：

   ```bash
   python main.py authorize xxx.txt
   ```

5. 然后就搞定啦

