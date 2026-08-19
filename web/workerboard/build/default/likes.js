export default {
    async fetch( request ) {
        const { post_id, author_name, author_id, viewer_id, viewer_name, like_ids, is_private } = await request.json();

        let options = { headers: { "Content-Type": "text/html; charset=utf-8" } }

        if ( author_id === viewer_id ) {
            return new Response( "omg!!! you're me!!! and i'm you!!!", options )
        }

        if ( like_ids.includes( viewer_id ) ) {
            return new Response( "whoa... you LOVE me... you want me ALIVE 🥺", options )
        }

        return new Response( "you havent liked my post... you HATE me... you want me DEAD 😡", options )
    },
};