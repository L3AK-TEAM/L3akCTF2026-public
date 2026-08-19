export default {
    async fetch( request ) {
        const { post_id, author_name, author_id, viewer_id, viewer_name, like_ids, is_private } = await request.json();

        let flag = "nothing to see here...";

        if ( author_id === viewer_id && viewer_name === author_name ) {
            flag = "L3AK{not_the_real_flag_i_think_maybe_idk_i_forgot_sorry}"
        }

        return new Response(
            "<main style=\"font: 16px system-ui; padding: 2rem\">" +
            "<h1>" + author_name + "'s secret storage</h1>" +
            "<p>" + flag + "</p></main>",
            { headers: { "Content-Type": "text/html; charset=utf-8" } },
        );
    },
};