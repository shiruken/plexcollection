import requests
from xml.etree import ElementTree
from plexapi.server import PlexServer


PLEX_URL = ""
PLEX_TOKEN = ""
TRAKT_TOKEN = ""


class PlexMovieLibrary(object):

    def __init__(self, plex_url, plex_token, library_name):
        self.plex_url = plex_url
        self.plex_token = plex_token
        self.plex = PlexServer(self.plex_url, self.plex_token)
        self.library = self.plex.library.section(library_name)
        self.get_movie_library()

    def get_movie_library(self):
        """Populate dictionary mapping imdb_id to movie object for all movies in library"""
        self.movies = {}
        for movie in self.library.all():
            imdb_id = self.get_imdb_id(movie)

            if imdb_id:
                self.movies[imdb_id] = movie
            else:
                print(f"Missing IMDb id for {movie.title} ({movie.year})")

        print(f"\nFound {len(self.movies)} movies in Plex Library '{self.library.title}'\n")

    def get_movies_in_collection(self, collection_name):
        """Returns list of IMDb ids for all movies currently in a Plex collection"""
        movies_in_collection = self.library.search(collection=collection_name)
        imdb_ids = []
        for movie in movies_in_collection:
            imdb_id = list(self.movies.keys())[list(self.movies.values()).index(movie)]
            imdb_ids.append(imdb_id)

        if movies_in_collection:
            print(f"{len(movies_in_collection)} movies are currently in the collection\n")
        else:
            print(f"The '{collection_name}' collection does not exist on Plex\n")
        return imdb_ids

    def get_imdb_id(self, movie):
        """Directly queries Plex Media Server to get IMDb id from metadata
        The new Plex Movie scanner uses a Plex-generated guid to identify
        movie objects instead of the previously-used IMDb id. The PlexAPI
        python module has yet to be updated to access the new `Guid` metadata
        elements containing both the IMDb and TMDb ids.
        """
        url = f"{self.plex_url}/library/metadata/{movie.ratingKey}?X-Plex-Token={self.plex_token}"
        request = requests.get(url)
        root = ElementTree.fromstring(request.text)
        for guid in root.iter('Guid'):
            if "imdb://" in guid.get("id"):
                return guid.get("id").split("imdb://")[1]

        return None

    def update_collection(self, trakt_list_url, collection_name):
        """Create/update collection with movies in Trakt list"""
        
        print("===================================================================")
        print(f"Updating '{collection_name}' collection")
        print("===================================================================")

        imdb_ids = self.get_movies_in_collection(collection_name)

        # Add movies to collection
        added_count = 0
        missing = []
        for movie in get_trakt_list(trakt_list_url):
            imdb_id = movie["movie"]["ids"]["imdb"]
            title = movie["movie"]["title"]
            year = movie["movie"]["year"]

            if imdb_id in self.movies:
                if imdb_id not in imdb_ids:
                    self.movies[imdb_id].addCollection(collection_name)
                    print(f"  Added {title} ({year})")
                    added_count += 1
                else:
                    imdb_ids.remove(imdb_id)
            else:
                missing.append(movie)

        if added_count > 0:
            print(f"\nAdded {added_count} movies to the collection\n")

        # Remove movies from collection that are no longer on the list
        for imdb_id in imdb_ids:
            self.movies[imdb_id].removeCollection(collection_name)
            print(f"  Removed {self.movies[imdb_id].title} ({self.movies[imdb_id].year})")

        if len(imdb_ids) > 0:
            print(f"\nRemoved {len(imdb_ids)} movies from the collection\n")

        # Print missing movies
        if len(missing) > 0:
            print(f"Missing {len(missing)} movies:\n")
            for entry in missing:
                title = entry["movie"]["title"]
                year = entry["movie"]["year"]
                print(f"  {title} ({year})")
        else:
            print("Congrats! Your collection is complete!")

        print("")


def get_trakt_list(url):
    """Returns JSON for Trakt list"""
    list_name = url.split("/users/")[1].split("?")[0]
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": TRAKT_TOKEN
    }
    url = f"https://api.trakt.tv/users/{list_name}/items/movies"
    request = requests.get(url, headers=headers)
    return request.json()


if __name__ == "__main__":

    library = PlexMovieLibrary(PLEX_URL, PLEX_TOKEN, "Movies")

    url_reddit_top250 = "https://trakt.tv/users/jay-greene/lists/reddit-top-250-2019-edition"
    library.update_collection(url_reddit_top250, "Reddit Top 250")

    url_imdb_top250 = "https://trakt.tv/users/justin/lists/imdb-top-rated-movies"
    library.update_collection(url_imdb_top250, "IMDb Top 250")

    url_bestpicture = "https://trakt.tv/users/thefork/lists/academy-awards-best-picture-winners"
    library.update_collection(url_bestpicture, "Academy Award for Best Picture")

    url_disney = "https://trakt.tv/users/movistapp/lists/walt-disney-animated-feature-films"
    library.update_collection(url_disney, "Walt Disney Animation Studios")
