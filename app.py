from base64 import *
from hashlib import *

import requests
from flask import *
from pymysql import *
from config import *

app = Flask(__name__)
app.secret_key = secretKey
db = connect(
    host=dbHost,
    port=dbPort,
    user=dbUser,
    password=dbPass,
    database=dbName
)


@app.route('/api/index')
def index():
    return '文章管理系统'


@app.route('/api/login', methods=['POST'])
def login():
    userInfo = request.get_json()
    cur = db.cursor()
    cur.execute(f"select password from users where username='{userInfo['username']}'")
    res = cur.fetchone()
    print(res)
    if res is None:
        return jsonify({"error": "用户不存在"})
    if res[0] != md5(userInfo['password'].encode()).hexdigest():
        return jsonify({"error": "密码错误"})
    session['username'] = userInfo['username']
    return jsonify({"message": "登陆成功"})


@app.route('/api/register', methods=['POST'])
def register():
    userInfo = request.get_json()
    if userInfo['password'] != userInfo['passwordVerify']:
        return jsonify({"error": "两次密码不一致"})
    cur = db.cursor()
    cur.execute(f"select * from users where username='{userInfo['username']}'")
    print(cur.fetchall())
    if cur.fetchone() is not None:
        return jsonify({"error": "用户名已存在"})
    cur.execute(
        f"insert into fcw.users (id,username,password,registerdate) values (null,'{userInfo['username']}','{(md5(userInfo['password'].encode())).hexdigest()}',now());")
    db.commit()
    cur.close()
    session['username'] = userInfo['username']
    return jsonify({"message": "注册成功"}) and redirect('/home')


@app.route('/api/getInfo', methods=['POST'])
def getInfo():
    if 'username' not in session.keys():
        return redirect('/login')
    print(session)
    cur = db.cursor()
    cur.execute(f"select avatar,registerdate from users where username='{session['username']}'")
    res = cur.fetchone()
    userInfo = dict()
    userInfo['avatar'] = res[0]
    userInfo['registerdate'] = res[1]
    cur.execute(f"select title,content,time from posts where author='{session['username']}'")
    res = list(cur.fetchall())
    userInfo['posts'] = []
    for raw in res:
        post = dict()
        post['title'] = raw[0]
        post['content'] = raw[1]
        post['time'] = raw[2]
        post['author'] = session['username']
        userInfo['posts'].append(post)
    return jsonify(userInfo)


@app.route('/api/makePost', methods=['POST'])
def makePost():
    if 'username' not in session.keys():
        return redirect('/login')
    post = request.get_json()
    post['author'] = session['username']
    cur = db.cursor()
    cur.execute(
        f"insert into posts (id, author, title, content, time) values (null,'{post['author']}','{post['title']}','{post['content']}',now())")
    db.commit()
    return jsonify({"message": "发布成功"})


@app.route('/api/postList', methods=['POST'])
def postList():
    if 'username' not in session.keys():
        return redirect('/login')
    page = request.get_json()['page']
    cur = db.cursor()
    cur.execute(f"select id,author,title,content,time from posts")
    res = cur.fetchall()
    return jsonify({
        "posts": res[(page - 1) * 10:(page - 1) * 10 + 10]
    })


@app.route('/api/commentList', methods=['POST'])
def commentList():
    if 'username' not in session.keys():
        return redirect('/login')
    id = request.get_json()['id']
    cur = db.cursor()
    cur.execute(f"select * from comments where post={id}")
    List = []
    for raw in cur.fetchall():
        comment = dict()
        comment['id'] = raw[0]
        comment['author'] = raw[1]
        comment['content'] = raw[3]
        comment['time'] = raw[4]
        List.append(comment)
    return jsonify({"comments": List})


@app.route('/api/makeComment', methods=['POST'])
def makeComment():
    if 'username' not in session.keys():
        return redirect('/login')
    comment = request.get_json()
    comment['author'] = session['username']
    cur = db.cursor()
    cur.execute(
        f"insert into comments (id, author, post, content, time) values (null,'{comment['author']}',{comment['post']},'{comment['content']}',now())")
    db.commit()
    return jsonify({"message": "发表成功"})


@app.route('/api/delComment', methods=['POST'])
def delComment():
    if 'username' not in session.keys():
        return redirect('/')
    cid = request.get_json()['id']
    cur = db.cursor()
    cur.execute(f"select author from comments where id={cid}")
    res = cur.fetchone()
    if res is None:
        return jsonify({"error": "评论不存在"})
    if res[0] != session['username']:
        return jsonify({"error": "无权限"})
    cur.execute(f"delete from comments where id={cid}")
    db.commit()
    return jsonify({"message": "删除成功"})


@app.route('/ai/editPost', method=['POST'])
def editPost():
    if 'username' not in session.keys():
        return redirect('/')
    post = request.get_json()
    cur = db.cursor()
    cur.execute(f"select author from posts where id={post['id']}")
    if session['username'] != cur.fetchone()[0]:
        return jsonify({"error": "无权限"})
    else:
        cur.execute(f"update posts set tiltle='{post['title']}',content='{post['content']}',time=now()")
        db.commit()
    return jsonify({"message": "修改成功"})


@app.route('/api/delPost', methods=['POST'])
def delPost():
    if 'username' not in session.keys():
        return redirect('/')
    pid = request.get_json()['id']
    cur = db.cursor()
    cur.execute(f"select author from posts where id={pid}")
    res = cur.fetchone()
    if res is None:
        return jsonify({"error": "文章不存在"})
    if res[0] != session['username']:
        return jsonify({"error": "无权限"})
    cur.execute(f"delete from posts where id={pid}")
    db.commit()
    return {"massage": "删除成功"}


@app.route('/api/reportComment', methods=['POST'])
def reportComment():
    if 'username' not in session.keys():
        return redirect('/')
    cid = request.get_json()['id']
    cur = db.cursor()
    cur.execute(f"select author from comments where id={cid}")
    res = cur.fetchone()
    if res is None:
        return jsonify({"error": "评论不存在"})
    cur.execute(f"insert into reportted set type=1,id={cid}")
    db.commit()
    return jsonify({"message": "举报成功，等待管理员审核"})


@app.route('/api/reportPost', methods=['POST'])
def reportPost():
    if 'username' not in session.keys():
        return redirect('/login')
    pid = request.get_json()['id']
    cur = db.cursor()
    cur.execute(f"select author from posts where id={pid}")
    res = cur.fetchone()
    if res is None:
        return jsonify({"error": "评论不存在"})
    cur.execute(f"insert into reportted set type=2,id={pid}")
    db.commit()
    return jsonify({"message": "举报成功，等待管理员审核"})


@app.route('/api/changePassword')
def changePassword():
    if 'username' not in session.keys():
        return redirect('/')
    currentUser = session['username']
    cur = db.cursor()
    cur.execute(f"select password from users where username='{currentUser}'")
    oldPwd = cur.fetchone()[0]
    newInfo = request.get_json()
    if oldPwd != newInfo['oldPwd']:
        return jsonify({"error": "原密码不正确"})
    if newInfo['newPwd'] != newInfo['newPwdVerify']:
        return jsonify({"error": "两次密码吗不一致"})
    cur.execute(f"update users set password='{md5(newInfo['newPwd'].encode()).hexdigest()}'")
    db.commit()
    return jsonify({"message": "修改成功"})


@app.route('/admin/reportedList', methods=['POST'])
def reportedList():
    if 'username' not in session.keys():
        return redirect('/')
    if session['username'] != 'admin':
        return redirect('/')
    body = request.get_json()
    cur = db.cursor()
    if body['type'] == 1:
        cur.execute(f"select id from reportted where type=1")
    elif body['type'] == 2:
        cur.execute(f"select id from reportted where type=2")
    else:
        return jsonify({"error": "类型错误"})
    res = cur.fetchall()
    response = {"list": []}
    for id in res:
        if not id:
            continue
        response['list'].append(id[0])
    return jsonify(response)


@app.route('/admin/delSth', methods=['POST'])
def delSth():
    try:
        if session['username'] != 'admin':
            return redirect('/')
    except KeyError:
        return redirect('/')
    body = request.get_json()
    cur = db.cursor()
    if body['type'] == 1:
        cur.execute(f"delete from comments where id={body['id']}")
    elif body['type'] == 2:
        cur.execute(f"delete from posts where id={body['id']}")
    else:
        return jsonify({"error": "类型错误"})
    db.commit()
    return jsonify({"message": "删除成功"})

if __name__ == '__main__':
    app.run()
