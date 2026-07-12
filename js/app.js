const IMG =
"https://image.tmdb.org/t/p/w500";


let selectedMovie = null;

let currentSeries = null;



// CARD CREATE

function createCard(movie){

    if(!movie.poster_path)
        return "";

    let title =
    movie.title || movie.name;


    return `

    <div class="card"
    onclick='openDetails(${JSON.stringify(movie)})'>


        <img src="${IMG}${movie.poster_path}">


        <h3>${title}</h3>


        <div class="rating">
        ⭐ ${movie.vote_average?.toFixed(1) || "0"}
        </div>


    </div>

    `;

}





// LOAD HOME DATA

async function loadHome(){


    let trending =
    await getTrending();


    document.getElementById("trending")
    .innerHTML =
    trending.results
    .map(createCard)
    .join("");



    let movies =
    await getPopularMovies();


    document.getElementById("movies")
    .innerHTML =
    movies.results
    .map(createCard)
    .join("");



    let series =
    await getPopularSeries();


    document.getElementById("series")
    .innerHTML =
    series.results
    .map(createCard)
    .join("");

}




loadHome();







// DETAILS PAGE


function openDetails(movie){


    selectedMovie = movie;


    document.getElementById(
    "detailPoster"
    ).src =
    IMG + movie.poster_path;



    document.getElementById(
    "detailTitle"
    ).innerText =
    movie.title || movie.name;



    document.getElementById(
    "detailText"
    ).innerText =
    movie.overview || "No description";



    document.getElementById(
    "detailsModal"
    ).style.display="flex";



}






function closeDetails(){

    document.getElementById(
    "detailsModal"
    ).style.display="none";

}








// PLAY MOVIE


function playMovie(){


let id = selectedMovie.id;


let type =
selectedMovie.media_type || "movie";



let url;



if(type==="tv"){


url =
`https://vidsrc.pm/embed/tv/${id}`;


}else{


url =
`https://vidsrc.pm/embed/movie/${id}`;


}



document.getElementById(
"player"
).src=url;



document.getElementById(
"detailsModal"
).style.display="none";



document.getElementById(
"playerModal"
).style.display="flex";


}







function closePlayer(){


document.getElementById(
"player"
).src="";



document.getElementById(
"playerModal"
).style.display="none";


}







// TRAILER


async function openTrailer(){


let data =
await getMovieVideos(
selectedMovie.id
);



let trailer =
data.results.find(
v=>v.type==="Trailer"
);



if(trailer){


window.open(
`https://youtube.com/watch?v=${trailer.key}`
);


}


}









// SERIES



async function openSeries(movie){


currentSeries = movie;



document.getElementById(
"seriesName"
).innerText =
movie.name;



document.getElementById(
"seriesModal"
).style.display="flex";



let data =
await getSeriesDetails(movie.id);



let season =
document.getElementById(
"seasonSelect"
);



season.innerHTML="";



for(
let i=1;
i<=data.number_of_seasons;
i++
){


season.innerHTML +=
`

<option value="${i}">
Season ${i}
</option>

`;


}



loadEpisodes();


}







async function loadEpisodes(){


let season =
document.getElementById(
"seasonSelect"
).value;



let data =
await getEpisodes(
currentSeries.id,
season
);



let ep =
document.getElementById(
"episodeSelect"
);



ep.innerHTML="";



data.episodes.forEach(e=>{


ep.innerHTML +=

`

<option value="${e.episode_number}">

Episode ${e.episode_number}
-
${e.name}

</option>

`;


});


}







function playEpisode(){



let season =
document.getElementById(
"seasonSelect"
).value;



let episode =
document.getElementById(
"episodeSelect"
).value;



document.getElementById(
"player"
).src =

`https://vidsrc.pm/embed/tv/${currentSeries.id}/${season}/${episode}`;



document.getElementById(
"seriesModal"
).style.display="none";



document.getElementById(
"playerModal"
).style.display="flex";


}







function closeSeries(){


document.getElementById(
"seriesModal"
).style.display="none";


}