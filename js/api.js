const API_KEY = "YOUR_TMDB_API_KEY";

const API = "https://api.themoviedb.org/3";


async function apiFetch(url){

    const response = await fetch(url);

    const data = await response.json();

    return data;

}



async function getTrending(){

    return await apiFetch(
    `${API}/trending/all/week?api_key=${API_KEY}&language=en-US`
    );

}



async function getPopularMovies(){

    return await apiFetch(
    `${API}/movie/popular?api_key=${API_KEY}&language=en-US`
    );

}



async function getPopularSeries(){

    return await apiFetch(
    `${API}/tv/popular?api_key=${API_KEY}&language=en-US`
    );

}



async function getMovieVideos(id){

    return await apiFetch(
    `${API}/movie/${id}/videos?api_key=${API_KEY}`
    );

}



async function getSeriesDetails(id){

    return await apiFetch(
    `${API}/tv/${id}?api_key=${API_KEY}`
    );

}



async function getEpisodes(id,season){

    return await apiFetch(
    `${API}/tv/${id}/season/${season}?api_key=${API_KEY}`
    );

}