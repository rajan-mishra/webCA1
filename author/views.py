from flask import Blueprint, request, render_template, url_for,session, redirect, flash
from werkzeug.security import generate_password_hash
from urllib.parse import urlparse
from urllib.parse import urljoin
from opencage.geocoder import OpenCageGeocode
from urllib.request import urlopen
import json

from author.models import Author
from author.forms import RegisterForm, LoginForm, AddressForm
from application import db
from author.decorators import login_required

author_app = Blueprint("author_app", __name__)

key = '2d4978b63c7f451fa89976d4bb779136'
geocoder = OpenCageGeocode(key)

class Place(object):
  def meters_to_walking_time(self, meters):
      return int(meters / 80)

  def wiki_path(self, slug):
      return urljoin( 'http://en.wikipedia.org/wiki/', slug.replace(' ', '_'))

  def address_to_latlng(self, address):
      results = geocoder.geocode(address)
      lat = results[0]['geometry']['lat']
      lng = results[0]['geometry']['lng']

      return (lat, lng)

  def query(self, address):

    results = geocoder.geocode(address)
    lat = results[0]['geometry']['lat']
    lng = results[0]['geometry']['lng']

    query_url = 'https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord={0}%7C{1}&gsradius=5000&gslimit=20&format=json'.format(lat, lng)
    g = urlopen(query_url)

    results = g.read()

    g.close()

    data = json.loads(results)

    places = []
    for place in data['query']['geosearch']:
      name = place['title']
      meters = place['dist']
      lat = place['lat']
      lng = place['lon']

      wiki_url = self.wiki_path(name)
      walking_time = self.meters_to_walking_time(meters)

      d = {
        'name': name,
        'url': wiki_url,
        'time': walking_time,
        'lat': lat,
        'lng': lng
      }

      places.append(d)

    return places




@author_app.route('/register', methods = ['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        author = Author(
        form.full_name.data,
        form.email.data,
        hashed_password
        )
        db.session.add(author)
        db.session.commit()
        flash("You have successfully registered", "success")
        return render_template("author/login.html", form=form)
    return render_template("author/register.html", form=form)

@author_app.route('/login', methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    error = None

    if request.method == "GET" and request.args.get("next"):
        session["next"] = request.args.get("next", None)
    if form.validate_on_submit():
        author = Author.query.filter_by(email=form.email.data).first()
        session['id'] = author.id
        session['full_name'] = author.full_name
        if 'next' in session:
            next = session.get('next')
            session.pop('next')
            return redirect(next)
        else:
            return redirect(url_for("blog_app.index"))

    return render_template("author/login.html", form=form, error = error)

@author_app.route('/geo_location', methods=['GET','POST'])
@login_required
def geo_location():
    form = AddressForm()

    places = []

    my_coordinates = (37.4221,-122.08)

    if request.method == "POST" :
        if form.validate() == False:
            return render_template("author/geo.html", form= form)
        else:
            address = form.address.data

            p = Place()
            my_coordinates = p.address_to_latlng(address)
            places = p.query(address)

            return render_template("author/geo.html", form=form, my_coordinates = my_coordinates, places=places)

    return render_template("author/geo.html", form= form, my_coordinates=my_coordinates, places=places, geo = True)


@author_app.route('/logout')
def logout():
    session.pop ("id")
    session.pop("full_name")
    flash("You have been successfully logged out ", "success")
    return redirect(url_for(".login"))
