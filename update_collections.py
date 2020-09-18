import requests
from xml.etree import ElementTree
from plexapi.server import PlexServer


PLEX_URL = ""
PLEX_TOKEN = ""
TRAKT_TOKEN = ""


def get_imdb_id(movie):
    """Directly queries Plex Media Server to get IMDb id from metadata
    The new Plex Movie scanner uses a Plex-generated guid to identify
    movie objects instead of the previously-used IMDb id. The PlexAPI
    python module has yet to be updated to access the new `Guid` metadata
    elements containing both the IMDb and TMDb ids.
    """
    url = f"{PLEX_URL}/library/metadata/{movie.ratingKey}?X-Plex-Token={PLEX_TOKEN}"
    request = requests.get(url)
    root = ElementTree.fromstring(request.text)
    for guid in root.iter('Guid'):
        if "imdb://" in guid.get("id"):
            return guid.get("id").split("imdb://")[1]

    return None


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


def populate_collection(trakt_list_url, collection):
    """Adds/removes movies to collection based on Trakt list"""
    
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    library = plex.library.section('Movies')

    print("===================================================================")
    print(f"Updating '{collection}' collection")
    print("===================================================================")

    # Create dictionary of all movies in Plex library {imdb_id: movie}
    # Flag which movies are already in the collection
    movies = {}
    movies_in_collection = library.search(collection=collection)
    movies_in_collection_imdb = []
    for movie in library.all():
        imdb_id = get_imdb_id(movie)

        if imdb_id:
            movies[imdb_id] = movie
            if movie in movies_in_collection:
                movies_in_collection_imdb.append(imdb_id)
        else:
            print(f"Missing IMDb id for {movie.title} ({movie.year})")

    print(f"Found {len(movies)} movies in Plex. {len(movies_in_collection)} are currently in the collection.\n")

    # Get list of movies from Trakt and add movies to the collection
    added_count = 0
    movies_missing = []
    for movie in get_trakt_list(trakt_list_url):
        imdb_id = movie["movie"]["ids"]["imdb"]
        title = movie["movie"]["title"]
        year = movie["movie"]["year"]

        if imdb_id in movies:
            if imdb_id not in movies_in_collection_imdb:
                movies[imdb_id].addCollection(collection)
                print(f"Added {title} ({year})")
                added_count += 1
            else:
                movies_in_collection_imdb.remove(imdb_id)
        else:
            movies_missing.append(movie)

    if added_count > 0:
        print(f"Added {added_count} movies to the collection\n")

    # Remove movies from collection that are no longer on the list
    for imdb_id in movies_in_collection_imdb:
        movies[imdb_id].removeCollection(collection)
        print(f"Removed {movies[imdb_id].title} ({movies[imdb_id].year})")

    if len(movies_in_collection_imdb) > 0:
        print(f"Removed {len(movies_in_collection_imdb)} movies from the collection\n")

    # Print missing movies
    if len(movies_missing) > 0:
        print(f"Missing {len(movies_missing)} movies:\n")
        for entry in movies_missing:
            title = entry["movie"]["title"]
            year = entry["movie"]["year"]
            print(f"  {title} ({year})")
    else:
        print("Congrats! Your collection is complete!")
        
    print("")


if __name__ == "__main__":
    url_reddit_top250 = "https://trakt.tv/users/jay-greene/lists/reddit-top-250-2019-edition"
    populate_collection(url_reddit_top250, "Reddit Top 250")

    url_imdb_top250 = "https://trakt.tv/users/justin/lists/imdb-top-rated-movies"
    populate_collection(url_imdb_top250, "IMDb Top 250")

    url_bestpicture_winners = "https://trakt.tv/users/thefork/lists/academy-awards-best-picture-winners"
    populate_collection(url_bestpicture_winners, "Academy Award for Best Picture")

    url_disneyanimated = "https://trakt.tv/users/movistapp/lists/walt-disney-animated-feature-films"
    populate_collection(url_disneyanimated, "Walt Disney Animation Studios")
