export default {
    async fetch( request ) {
        const { post_id, author_name, author_id, viewer_id, viewer_name, like_ids, is_private } = await request.json();


        return new Response( "<p>would any of you happen to know where i could obtain some number of grapes? any help would be greatly appreciated, thank you</p>", { headers: { "Content-Type": "text/html; charset=utf-8" } } )
    },
};