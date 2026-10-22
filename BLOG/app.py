from flask import Flask,flash, render_template,request,redirect,url_for,session
from werkzeug.security import check_password_hash,generate_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key="flask_blog"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:root@localhost:3306/blog'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db=SQLAlchemy(app)

likes = db.Table('likes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('post_id', db.Integer, db.ForeignKey('blogger.id'))
)

class Blogger(db.Model):
    id = db.Column(db.Integer, primary_key=True) 
    description = db.Column(db.Text(500))
    image = db.Column(db.String(255))
    title = db.Column(db.String(255))
    author = db.Column(db.String(255))
    category = db.Column(db.String(50))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True,  nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(50))
    liked = db.relationship('Blogger', secondary=likes, backref=db.backref('likers', lazy='dynamic'))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('blogger.id'), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/', methods=['GET'])
def index():
    selected_category = request.args.get('category')
    search = request.args.get('search', '')
    
    query = Blogger.query

    if selected_category:
        query = query.filter_by(category=selected_category)

    if search:
        query = query.filter(
            (Blogger.title.ilike(f'%{search}%')) |
            (Blogger.description.ilike(f'%{search}%'))
        )
    
    posts = query.all()
    categories = db.session.query(Blogger.category).distinct().all()

    return render_template('index.html', posts=posts, categories=categories, search=search, selected_category=selected_category)

@app.route('/travel', methods=['GET'])
def travel():
    travel_posts = Blogger.query.filter_by(category='travel').all()
    return render_template('travel.html',travel_posts=travel_posts)
    
@app.route('/food', methods=['GET'])
def food():
    food_posts = Blogger.query.filter_by(category='food').all()
    return render_template('food.html',food_posts=food_posts)

@app.route('/studies', methods=['GET'])
def studies():
 
    studies_posts = Blogger.query.filter_by(category='studies').all()
    return render_template('studies.html',studies_posts=studies_posts)


@app.route('/ai', methods=['GET'])
def ai():
    ai_posts = Blogger.query.filter_by(category='ai').all()
    return render_template('ai.html',ai_posts=ai_posts)



@app.route('/register',methods=['GET','POST'])
def register():
    error=None
    if request.method == 'POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        role=request.form['role']
         
        user_exist=User.query.filter_by(username=username).first()
        if user_exist:
             error='The username already exists'
             return render_template('register.html',error=error)
        
        hashed_password=generate_password_hash(password)
        new_user=User(username=username,password=hashed_password,role=role,email=email)
      
        db.session.add(new_user)
        db.session.commit()
        flash('Your account created successfully','success')
        return redirect(url_for('login'))
    return render_template('register.html')
           

    
@app.route('/login',methods=['GET','POST'])
def login():
    error= None
    if request.method == 'POST':
      username=request.form['username']
      password=request.form['password']
      role=request.form['role']
      user= User.query.filter_by(username=username,role=role).first()
      if  user and  check_password_hash(user.password,password):
         session['username'] = user.username
         session['role'] = user.role
         session['email'] = user.email
         if user.role=='admin':
             return redirect( url_for('admin_dashboard'))
         else:
             flash(f'Welcome {username}, you have logged in successfully ','success')
             return redirect(url_for('dashboard'))
   
      else:
         error ='Invalid Credentials'
    return render_template('login.html',error=error)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.','error')
    return redirect(url_for('login'))

@app.route('/home_page', methods=['GET', 'POST'])
def home_page(): 
    if request.method == 'POST':
      title = request.form.get('title')
      image = request.files.get('image')
      description = request.form.get('description')
      author=session.get('username')
      category=request.form.get('category')
     
      if image and description and title and author and category:
            filename = secure_filename(image.filename)
            image.save(os.path.join('static/uploads', filename))

            new_comment = Blogger(description=description, image='uploads/' + filename, title=title, author=author, category=category)
            db.session.add(new_comment)
            db.session.commit()
            flash('Your blog has been created successfully','success')
           
            return redirect(url_for('dashboard'))        
        
    return render_template('home_page.html')

@app.route('/dashboard',methods=["GET"])
def dashboard():
    query = Blogger.query
    posts = query.all()
    liked_posts = []
    comments = Comment.query.order_by(Comment.timestamp.desc()).all() 
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
           liked_posts = user.liked if user else []
    return render_template('dashboard.html', posts=posts, liked_posts=liked_posts,comments=comments)

@app.route('/profile',methods=["GET"])
def profile():
   username = session.get('username')
   email = session.get('email')
   posts = Blogger.query.filter_by(author=username).all()
   return render_template('profile.html',username=username,email=email,posts=posts)

@app.route('/admin/comment/<int:blogger_id>', methods=['POST'])
def comment(blogger_id):
    comment_text = request.form['comment_text']
    new_comments = Comment(
        post_id=blogger_id,
        author=session.get('username'),
        text=comment_text
    )
    db.session.add(new_comments)
    db.session.commit()
    flash('Your comment has been added','success')
    return redirect(url_for('dashboard'))

@app.route('/admin/edit/<int:blogger_id>',methods=['GET', 'POST'])
def edit(blogger_id):
    post = Blogger.query.get_or_404(blogger_id)

    if request.method == 'POST':
        post.title = request.form['title']
        post.description = request.form['description']
        post.category = request.form['category']

        image = request.files.get('image')
        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join('static/uploads', filename))
            post.image = 'uploads/' + filename

        db.session.commit()
        flash('Your Blog has been updated successfully','success')
        return redirect(url_for('admin_dashboard'))

    return render_template('edit.html', post=post)

@app.route('/admin/edit_comment/<int:comment_id>',methods=['GET', 'POST'])
def edit_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if request.method =='POST':
        comment.text = request.form['comment_text']
        db.session.commit()
        flash('Your comment has been updated successfully','success')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_comment.html', comment=comment)


@app.route('/admin/delete/<int:blogger_id>',methods=['GET','POST'])
def delete(blogger_id):
    post=Blogger.query.get_or_404(blogger_id)
    db.session.delete(post)
    db.session.commit()
    flash('Your blog has been deleted successfully','success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_comment/<int:comment_id>',methods=['GET','POST'])
def delete_comment(comment_id):
    comment=Comment.query.get_or_404(comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash('Your comment has been deleted successfully','error')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin_dashboard',methods=['GET'])
def admin_dashboard():  
    query = Blogger.query 
    posts=query.all()
    comments = Comment.query.order_by(Comment.timestamp.desc()).all()
    return render_template('admin_dashboard.html',posts=posts,comments=comments)


@app.route('/like<int:blogger_id>', methods=['POST'])
def like_post(blogger_id):
    post = Blogger.query.get_or_404(blogger_id)
    user = User.query.filter_by(username=session['username']).first()

    if post in user.liked:
        user.liked.remove(post)
        liked = False
    else:
        user.liked.append(post)
        liked = True
    likers_list = post.likers.all()
    db.session.commit()
    return redirect(url_for('dashboard'))


if __name__=='__main__':
    with app.app_context():
     db.create_all()
    app.run(debug='True') 