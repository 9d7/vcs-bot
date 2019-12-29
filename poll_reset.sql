SELECT MAX(O.OptionID) AS OptionID,
           MAX(Emoji) AS Emoji,
           MAX(Option) AS Option,
           COUNT(V.Username) AS VoteCount,
           VoteCount || ' ' ||
               (CASE WHEN VoteCount=1 THEN "vote"
                   ELSE "votes" END) AS VoteStr,
           STRING_AGG(V.Username, ' ') AS Votes
    FROM Options AS O
    LEFT OUTER JOIN Votes AS V
    ON O.OptionID=V.OptionID
    WHERE O.PollID=1
    GROUP BY O.OptionID
    ORDER BY
        VoteCount DESC,
        OptionID;